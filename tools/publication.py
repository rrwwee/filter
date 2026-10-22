"""Read-only publication and completion gates; never publish or mutate GitHub state."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SHA = re.compile(r'^[0-9a-f]{40}$')
REPO = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
REF = r'(?:https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/[1-9][0-9]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*|#[1-9][0-9]*)'
CLOSING = re.compile(r'\b(?:close[sd]?|fix(?:es|ed)?|resolve[sd]?)\b\s*:?\s*(' + REF + r'(?:\s*(?:,|and|&)\s*' + REF + r')*)', re.I)
REFERENCES = re.compile(REF, re.I)
QUERY = '''query($owner:String!,$name:String!,$number:Int!,$after:String){repository(owner:$owner,name:$name){nameWithOwner defaultBranchRef{name target{oid}} pullRequest(number:$number){number state headRefOid title body baseRefName headRepository{nameWithOwner} merged mergeCommit{oid} closingIssuesReferences(first:100,after:$after){totalCount nodes{number repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}}}}'''


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def issue_ref(value, repository):
    require(isinstance(value, str), 'Issue reference must be text')
    match = re.fullmatch(r'https?://github\.com/([^/]+/[^/]+)/(?:issues|pull)/([1-9][0-9]*)', value, re.I)
    if match:
        value = match[1] + '#' + match[2]
    if value.startswith('#'):
        value = repository + value
    match = re.fullmatch(r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#([1-9][0-9]*)', value)
    require(match is not None, 'Invalid issue reference')
    return value.lower()


def closing_references(text, repository):
    # Negation, code fences and quotes are deliberately not exemptions.
    return {issue_ref(ref[0], repository) for match in CLOSING.finditer(text)
            for ref in REFERENCES.finditer(match[1])}


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    require(result.returncode == 0, 'Read-only command failed: ' + command[0])
    return result.stdout


class Forge:
    def __init__(self, repository, reader=None):
        require(REPO.fullmatch(repository) is not None, 'Invalid repository')
        self.repository = repository.lower()
        self.reader = reader or (lambda args: json.loads(run(['gh', 'api', *args])))

    def snapshot(self, number):
        require(type(number) is int and number > 0, 'Invalid PR number')
        owner, name = self.repository.split('/')
        cursor, visited, references, baseline, total = None, set(), set(), None, None
        for _ in range(100):
            args = ['graphql', '-f', 'query=' + QUERY, '-f', 'owner=' + owner,
                    '-f', 'name=' + name, '-F', 'number=' + str(number)]
            if cursor is not None:
                args += ['-f', 'after=' + cursor]
            reply = self.reader(args)
            require(isinstance(reply, dict) and not reply.get('errors'), 'GraphQL error or missing response')
            data = reply.get('data')
            require(isinstance(data, dict), 'GraphQL data missing')
            repo = data.get('repository')
            require(isinstance(repo, dict) and repo.get('nameWithOwner', '').lower() == self.repository, 'Repository unavailable or mismatched')
            pr = repo.get('pullRequest')
            require(isinstance(pr, dict) and pr.get('number') == number, 'PR unavailable or mismatched')
            meta = {k: v for k, v in pr.items() if k != 'closingIssuesReferences'}
            meta['defaultBranch'] = repo.get('defaultBranchRef')
            require(SHA.fullmatch(meta.get('headRefOid', '')) and isinstance(meta.get('body'), str), 'Incomplete PR metadata')
            require(meta.get('state') in ('OPEN', 'CLOSED', 'MERGED') and type(meta.get('merged')) is bool, 'Unknown PR state')
            if baseline is None:
                baseline = meta
            require(meta == baseline, 'PR changed during pagination; read again')
            connection = pr.get('closingIssuesReferences')
            require(isinstance(connection, dict), 'Closing-reference connection missing')
            count, nodes, page = connection.get('totalCount'), connection.get('nodes'), connection.get('pageInfo')
            require(type(count) is int and count >= 0 and isinstance(nodes, list) and isinstance(page, dict), 'Incomplete closing-reference page')
            if total is None:
                total = count
            require(count == total and type(page.get('hasNextPage')) is bool and 'endCursor' in page, 'Inconsistent closing-reference pagination')
            for node in nodes:
                require(isinstance(node, dict) and type(node.get('number')) is int and node['number'] > 0, 'Invalid closing-reference node')
                linked_repo = node.get('repository')
                require(isinstance(linked_repo, dict), 'Missing linked repository')
                source = linked_repo.get('nameWithOwner')
                require(isinstance(source, str), 'Missing linked repository')
                ref = issue_ref(source + '#' + str(node['number']), self.repository)
                require(ref not in references, 'Duplicate closing-reference node')
                references.add(ref)
            if not page['hasNextPage']:
                require(len(references) == total, 'Incomplete closing-reference population')
                return {**baseline, 'closing': references}
            cursor = page['endCursor']
            require(isinstance(cursor, str) and cursor and cursor not in visited and nodes, 'Invalid or stalled closing-reference cursor')
            visited.add(cursor)
        raise GateError('Closing-reference pagination limit exceeded')

    def issue_state(self, reference):
        repository, number = reference.split('#')
        value = self.reader([f'repos/{repository}/issues/{number}'])
        require(isinstance(value, dict) and value.get('number') == int(number) and 'pull_request' not in value, 'Issue unavailable or wrong resource type')
        require(value.get('state') in ('open', 'closed'), 'Unknown issue state')
        return value['state']

    def landing(self, snapshot):
        require(snapshot['merged'] and snapshot['state'] == 'MERGED', 'PR has not landed')
        branch = snapshot.get('defaultBranch') or {}
        require(snapshot.get('baseRefName') == branch.get('name'), 'PR did not land on default branch')
        merge = (snapshot.get('mergeCommit') or {}).get('oid', '')
        head = (branch.get('target') or {}).get('oid', '')
        require(SHA.fullmatch(merge) and SHA.fullmatch(head), 'Missing merge/default-branch identity')
        compare = self.reader([f'repos/{self.repository}/compare/{merge}...{head}'])
        require(isinstance(compare, dict) and compare.get('status') in ('identical', 'ahead') and compare.get('merge_base_commit', {}).get('sha') == merge, 'Merge is not verified on default branch')
        checks, ids, total = [], set(), None
        for page in range(1, 101):
            value = self.reader([f'repos/{self.repository}/commits/{merge}/check-runs?filter=latest&per_page=100&page={page}'])
            require(isinstance(value, dict) and type(value.get('total_count')) is int and isinstance(value.get('check_runs'), list), 'Incomplete check-run page')
            if total is None:
                total = value['total_count']
            require(value['total_count'] == total and total >= 0, 'Check population changed')
            for check in value['check_runs']:
                require(isinstance(check, dict) and type(check.get('id')) is int and check['id'] not in ids and check.get('head_sha') == merge, 'Invalid, wrong-head or duplicate check run')
                ids.add(check['id']); checks.append(check)
            if len(checks) == total:
                require(any(c.get('name') == 'contracts' for c in checks), 'Required contracts check missing')
                require(all(c.get('status') == 'completed' and c.get('conclusion') in ('success', 'neutral', 'skipped') for c in checks), 'Landing checks pending or failed')
                require(all(c.get('conclusion') == 'success' for c in checks if c.get('name') == 'contracts'), 'Contracts check did not pass')
                return merge
            require(value['check_runs'] and len(checks) < total, 'Incomplete check-run population')
        raise GateError('Check pagination limit exceeded')


def publication(repository, head, messages, body, squash, intended, snapshot=None):
    require(SHA.fullmatch(head) is not None, 'Invalid head')
    require(isinstance(intended, list), 'Explicit completed-issue list required')
    expected = {issue_ref(r, repository) for r in intended}
    require(len(expected) == len(intended), 'Duplicate intended issue')
    require(all(isinstance(t, str) for t in [*messages, body, squash]), 'Publication metadata must be text')
    marked = intended_from_body(body)
    marked_set = {issue_ref(r, repository) for r in marked}
    require(len(marked_set) == len(marked), 'Duplicate issue in PR body marker')
    require(marked_set == expected, 'PR body marker differs from explicit completed-issue set')
    found = set().union(*(closing_references(t, repository) for t in [*messages, body, squash]))
    require(found <= expected, 'Unexpected closing references: ' + ', '.join(sorted(found - expected)))
    if snapshot is not None:
        require(snapshot['state'] == 'OPEN' and not snapshot['merged'], 'Pre-merge PR must be open')
        require(snapshot['headRefOid'] == head, 'PR head does not match reviewed local head')
        require(snapshot.get('headRepository', {}).get('nameWithOwner', '').lower() == repository.lower(), 'Unexpected head repository')
        require(snapshot['body'].rstrip('\n') == body.rstrip('\n'), 'Server PR body differs from proposed body')
        require(snapshot['closing'] == expected, 'Server closing links differ from explicit completed-issue set')
    return {'head': head, 'metadataChecked': True, 'forgeChecked': snapshot is not None,
            'closingIssues': sorted(expected), 'mergeAuthorization': False}


def completion(receipt, repository, forge=None, pr=None):
    require(isinstance(receipt, dict) and receipt.get('schema') == 1, 'Invalid completion receipt')
    status = receipt.get('status')
    require(status in ('local_complete', 'waiting_for_landing', 'blocked', 'assignment_complete'), 'Unknown completion status')
    require(isinstance(receipt.get('assignment'), str) and receipt['assignment'].strip(), 'Assignment scope required')
    require(SHA.fullmatch(receipt.get('head', '')) is not None and type(receipt.get('landingRequired')) is bool, 'Head and landing requirement required')
    declared = receipt.get('completedIssues')
    require(isinstance(declared, list), 'Receipt needs an explicit completed-issue list')
    intended = {issue_ref(r, repository) for r in declared}
    require(len(intended) == len(declared), 'Duplicate completed issue')
    criteria = receipt.get('acceptance')
    require(isinstance(criteria, list) and criteria, 'Acceptance reconciliation required')
    seen, unfinished = set(), set()
    for criterion in criteria:
        require(isinstance(criterion, dict) and isinstance(criterion.get('id'), str) and criterion['id'] and criterion['id'] not in seen and type(criterion.get('complete')) is bool, 'Invalid or duplicate acceptance criterion')
        seen.add(criterion['id'])
        require(not criterion['complete'] or isinstance(criterion.get('evidence'), str) and criterion['evidence'].strip(), 'Completed acceptance needs evidence')
        if criterion.get('issue') is not None and not criterion['complete']:
            unfinished.add(issue_ref(criterion['issue'], repository))
    require(status != 'blocked' or isinstance(receipt.get('blocker'), str) and receipt['blocker'].strip(), 'Blocked receipt needs a blocker')
    require(not (intended & unfinished), 'Cannot close an issue with unfinished acceptance')
    complete = status == 'assignment_complete'
    require(not complete or all(c['complete'] for c in criteria), 'Assignment has unfinished acceptance')
    merge = None
    if pr is not None:
        require(forge is not None, 'Forge reader required')
        snapshot = forge.snapshot(pr)
        require(snapshot['headRefOid'] == receipt['head'], 'Receipt head differs from forge head')
        if snapshot['merged']:
            require(snapshot['closing'] <= intended, 'Merged PR closed issues absent from receipt completed-issue set')
            require(not (snapshot['closing'] & unfinished), 'Merged partial slice closed unfinished acceptance')
            for issue in unfinished:
                require(forge.issue_state(issue) == 'open', 'Unfinished acceptance issue is not open')
        if complete and receipt['landingRequired']:
            merge = forge.landing(snapshot)
            for issue in intended:
                require(forge.issue_state(issue) == 'closed', 'Intended completed issue is not closed')
    require(not (complete and receipt['landingRequired']) or merge is not None, 'Assignment completion needs live landing readback')
    return {'status': status, 'assignmentComplete': complete, 'landingVerified': merge is not None,
            'mergeCommit': merge, 'receiptSha256': hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()}



def intended_from_body(body):
    markers = re.findall(r'<!--\s*filter-completed-issues:\s*(.*?)\s*-->', body, re.S)
    require(len(markers) == 1, 'PR body needs exactly one explicit filter-completed-issues JSON marker')
    intended = json.loads(markers[0])
    require(isinstance(intended, list), 'Completed-issue marker must contain a JSON list')
    return intended


def branch_messages(base, head):
    require(run(['git', 'rev-parse', 'HEAD']).strip() == head, 'Checkout differs from reviewed head')
    ancestors = run(['git', 'merge-base', '--all', base, head]).splitlines()
    require(len(ancestors) == 1, 'Unique branch merge base required')
    return run(['git', 'log', '--format=%B%x00', ancestors[0] + '..' + head]).split('\0')


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    pub = sub.add_parser('publication')
    pub.add_argument('--base', required=True); pub.add_argument('--body', type=Path, required=True)
    pub.add_argument('--squash', type=Path, required=True); pub.add_argument('--completed-issues', type=Path, required=True)
    event = sub.add_parser('publication-event'); event.add_argument('--event', type=Path, required=True)
    rec = sub.add_parser('receipt'); rec.add_argument('--file', type=Path, required=True)
    for p in (pub, rec):
        p.add_argument('--repo', required=True); p.add_argument('--pr', type=int)
    args = parser.parse_args(argv)
    try:
        if args.mode == 'publication-event':
            payload = json.loads(args.event.read_text())
            pr = payload['pull_request']; repository = pr['base']['repo']['full_name']
            forge = Forge(repository); head = pr['head']['sha']; body = pr['body'] or ''
            messages = branch_messages(pr['base']['sha'], head)
            snapshot = forge.snapshot(payload['number'])
            require(snapshot.get('title') == pr['title'], 'Server PR title changed')
            result = publication(repository, head, messages, body, pr['title']+'\n'+body, intended_from_body(body), snapshot)
        elif args.mode == 'publication':
            forge = Forge(args.repo)
            head = run(['git', 'rev-parse', 'HEAD']).strip()
            base = run(['git', 'rev-parse', '--verify', args.base + '^{commit}']).strip()
            messages = branch_messages(base, head)
            result = publication(args.repo, head, messages, args.body.read_text(), args.squash.read_text(), json.loads(args.completed_issues.read_text()), forge.snapshot(args.pr) if args.pr else None)
        else:
            result = completion(json.loads(args.file.read_text()), args.repo, Forge(args.repo), args.pr)
        print(json.dumps(result, sort_keys=True)); return 0
    except (GateError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print('Publication/completion gate failed: ' + str(error)); return 1
