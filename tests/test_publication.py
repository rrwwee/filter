"""Closing-reference examples stay in fixtures, never publication metadata."""
import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/publication.py'
SPEC = importlib.util.spec_from_file_location('publication', PATH)
P = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(P)
HEAD, MERGE = 'a'*40, 'b'*40
REPO = 'rrwwee/filter'
BODY = 'Related to #18\n<!-- filter-completed-issues: [] -->'


def page(nodes=(), more=False, cursor=None, total=None, merged=False):
    links=[{'number':n, 'repository':{'nameWithOwner':repo}} for repo,n in nodes]
    return {'data':{'repository':{'nameWithOwner':REPO,'defaultBranchRef':{'name':'main','target':{'oid':MERGE}},'pullRequest':{
        'number':23,'state':'MERGED' if merged else 'OPEN','headRefOid':HEAD,'title':'Research update','body':BODY,
        'baseRefName':'main','headRepository':{'nameWithOwner':REPO},'merged':merged,'mergeCommit':{'oid':MERGE} if merged else None,
        'closingIssuesReferences':{'totalCount':len(nodes) if total is None else total,'nodes':links,'pageInfo':{'hasNextPage':more,'endCursor':cursor}}}}}}


class PublicationTests(unittest.TestCase):
    def test_manual_command_reconciles_body_and_file_intent(self):
        import contextlib
        import io
        import json
        import tempfile
        from unittest.mock import patch

        cases = (
            ('Related to #18', [], 1),
            ('<!-- filter-completed-issues: [] --><!-- filter-completed-issues: [] -->', [], 1),
            ('<!-- filter-completed-issues: ["rrwwee/filter#18"] -->', [], 1),
            (BODY, [REPO+'#18'], 1),
            ('<!-- filter-completed-issues: ["rrwwee/filter#18", "RRWWEE/FILTER#18"] -->', [REPO+'#18'], 1),
            ('<!-- filter-completed-issues: invalid -->', [], 1),
            (BODY, [], 0),
            ('<!-- filter-completed-issues: ["RRWWEE/FILTER#18"] -->', [REPO+'#18'], 0),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'squash').write_text('Guard update')
            for body, intended, expected in cases:
                (root/'body').write_text(body)
                (root/'intent').write_text(json.dumps(intended))
                def read(command):
                    if command[0] == 'gh':
                        response = page([(REPO, 18)] if intended else [])
                        response['data']['repository']['pullRequest']['body'] = body
                        return json.dumps(response)
                    if command[1] == 'log':return ''
                    return HEAD if command == ['git', 'rev-parse', 'HEAD'] else MERGE
                for live in (False, True):
                    args = ['publication', '--repo', REPO, '--base', 'main',
                            '--body', str(root/'body'), '--squash', str(root/'squash'),
                            '--completed-issues', str(root/'intent')]
                    if live:args += ['--pr', '23']
                    with self.subTest(body=body, live=live), patch.object(P, 'run', side_effect=read), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(P.main(args), expected)

    def test_negation_case_colon_and_cross_repository_forms(self):
        for phrase in ('Does not close #18','CLOSES: #18','fixed:#18','Resolves other/repo#9',
                       'closed https://github.com/Other/Repo/issues/9','fixes #18, #19'):
            found=P.closing_references(phrase,REPO)
            self.assertTrue(found,phrase)
            with self.assertRaises(P.GateError):P.publication(REPO,HEAD,[phrase],BODY,'Research update',[])
        self.assertEqual(P.closing_references('Related to #18 and other/repo#9',REPO),set())
        self.assertEqual(P.closing_references('Resolved: OTHER/Repo#9',REPO),{'other/repo#9'})

    def test_all_publication_surfaces_are_scanned(self):
        for surface in range(3):
            text=[[], BODY, 'Research update']
            text[surface]=['Does not close #18'] if surface==0 else 'Does not close #18' + ('\n<!-- filter-completed-issues: [] -->' if surface==1 else '')
            with self.assertRaises(P.GateError):P.publication(REPO,HEAD,*text,[])
        out=P.publication(REPO,HEAD,['Related to #18'],BODY,'Research update',[])
        self.assertFalse(out['forgeChecked']);self.assertFalse(out['mergeAuthorization'])

    def test_complete_paginated_server_set_and_unexpected_manual_link(self):
        pages=iter([page([(REPO,18)],True,'next',2),page([('other/repo',9)],False,'done',2)])
        calls=[]
        forge=P.Forge(REPO,lambda args:(calls.append(args),next(pages))[1])
        snapshot=forge.snapshot(23)
        self.assertEqual(snapshot['closing'],{REPO+'#18','other/repo#9'})
        self.assertIn('after=next',calls[1])
        with self.assertRaises(P.GateError):P.publication(REPO,HEAD,[],BODY,'Research update',[],snapshot)
        body = 'Related to #18\n<!-- filter-completed-issues: ["rrwwee/filter#18", "other/repo#9"] -->'
        snapshot['body'] = body
        result=P.publication(REPO,HEAD,[],body,'Research update',[REPO+'#18','other/repo#9'],snapshot)
        self.assertTrue(result['forgeChecked'])

    def test_unknown_or_incomplete_server_data_never_becomes_empty(self):
        broken=[]
        for mutate in (
            lambda d:d.update(errors=[{'message':'denied'}]),
            lambda d:d.update(data=None),
            lambda d:d['data'].update(repository=None),
            lambda d:d['data']['repository']['pullRequest'].pop('closingIssuesReferences'),
            lambda d:d['data']['repository']['pullRequest']['closingIssuesReferences'].pop('pageInfo'),
            lambda d:d['data']['repository']['pullRequest']['closingIssuesReferences'].update(totalCount=1),
            lambda d:d['data']['repository']['pullRequest']['closingIssuesReferences'].update(pageInfo={'hasNextPage':True,'endCursor':None}),
        ):
            d=page();mutate(d);broken.append(d)
        for d in broken:
            with self.assertRaises(P.GateError):P.Forge(REPO,lambda _:d).snapshot(23)
        stalled=page([(REPO,18)],True,'same',2)
        with self.assertRaises(P.GateError):P.Forge(REPO,lambda _:stalled).snapshot(23)
        pages=iter([page([(REPO,18)],True,'n',2),page([(REPO,19)],False,'x',2)])
        first=next(pages);second=next(pages);second['data']['repository']['pullRequest']['headRefOid']='c'*40
        sequence=iter([first,second])
        with self.assertRaises(P.GateError):P.Forge(REPO,lambda _:next(sequence)).snapshot(23)

    def test_live_head_body_and_explicit_intent_must_agree(self):
        snapshot=P.Forge(REPO,lambda _:page()).snapshot(23)
        P.publication(REPO,HEAD,[],BODY,'Update',[],snapshot)
        for key,value in [('headRefOid','c'*40),('body','Changed'),('state','CLOSED')]:
            changed=copy.deepcopy(snapshot);changed[key]=value
            with self.assertRaises(P.GateError):P.publication(REPO,HEAD,[],BODY,'Update',[],changed)


    def test_large_connection_consumes_the_final_page(self):
        first=page([(REPO,n) for n in range(1,101)],True,'page2',103)
        last=page([(REPO,n) for n in range(101,104)],False,'done',103)
        responses=iter([first,last]);result=P.Forge(REPO,lambda _:next(responses)).snapshot(23)
        self.assertEqual(len(result['closing']),103);self.assertIn(REPO+'#103',result['closing'])

    def test_intent_marker_is_explicit_and_unique(self):
        self.assertEqual(P.intended_from_body('Related to #18\n<!-- filter-completed-issues: [] -->'),[])
        for body in ('Related to #18','<!-- filter-completed-issues: null -->',
                     '<!-- filter-completed-issues: [] --><!-- filter-completed-issues: [] -->'):
            with self.assertRaises(P.GateError):P.intended_from_body(body)

    def test_real_branch_log_preserves_all_messages(self):
        import subprocess
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=directory,text=True,stderr=subprocess.DEVNULL).strip()
            git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            git('commit','--allow-empty','-m','Base');base=git('rev-parse','HEAD')
            git('commit','--allow-empty','-m','Does not close #18')
            git('commit','--allow-empty','-m','Related to #19');head=git('rev-parse','HEAD')
            with patch.object(P,'run',side_effect=lambda command:subprocess.check_output(command,cwd=directory,text=True)):
                messages=P.branch_messages(base,head)
            with self.assertRaises(P.GateError):P.publication(REPO,head,messages,BODY,'Update',[])


    def test_event_rejects_stale_live_title(self):
        import contextlib
        import io
        import json
        import tempfile
        from unittest.mock import Mock, patch
        body='Related to #18\n<!-- filter-completed-issues: [] -->'
        payload={'number':23,'pull_request':{'title':'Research update','body':body,'head':{'sha':HEAD},'base':{'sha':MERGE,'repo':{'full_name':REPO}}}}
        snapshot=P.Forge(REPO,lambda _:page()).snapshot(23);snapshot['body']=body
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'event.json';path.write_text(json.dumps(payload))
            forge=Mock();forge.snapshot.return_value=snapshot
            with patch.object(P,'Forge',return_value=forge),patch.object(P,'branch_messages',return_value=[]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(P.main(['publication-event','--event',str(path)]),0)
                snapshot['title']='Different title'
                self.assertEqual(P.main(['publication-event','--event',str(path)]),1)


class ReceiptTests(unittest.TestCase):
    def test_assignment_completion_rejects_undeclared_merged_closure(self):
        receipt = self.receipt('assignment_complete')
        receipt['acceptance'][0].update(complete=True, evidence='Synthetic acceptance passed')
        def reader(args):
            if args[0] == 'graphql':return page([(REPO, 19)], merged=True)
            return self.reader(args)
        for landing in (True, False):
            for status in ('assignment_complete', 'local_complete', 'waiting_for_landing', 'blocked'):
                receipt.update(landingRequired=landing, status=status, blocker='Synthetic blocker')
                with self.subTest(landing=landing, status=status), self.assertRaisesRegex(P.GateError, 'absent from receipt'):
                    P.completion(receipt, REPO, P.Forge(REPO, reader), 23)

    def test_assignment_completion_accepts_declared_merged_closure(self):
        receipt = self.receipt('assignment_complete')
        receipt['acceptance'][0].update(complete=True, evidence='Synthetic acceptance passed')
        receipt['completedIssues'] = [REPO+'#18']
        def reader(args):
            if args[0] == 'graphql':return page([(REPO, 18)], merged=True)
            if '/issues/' in args[0]:return {'number':18, 'state':'closed'}
            return self.reader(args)
        result = P.completion(receipt, REPO, P.Forge(REPO, reader), 23)
        self.assertTrue(result['assignmentComplete'] and result['landingVerified'])

    def receipt(self,status='local_complete'):
        return {'schema':1,'assignment':'A bounded slice','status':status,'head':HEAD,'landingRequired':True,'completedIssues':[],
                'acceptance':[{'id':'criterion','issue':REPO+'#18','complete':False}]}

    def reader(self,args):
        if args[0]=='graphql':return page(merged=True)
        if '/issues/' in args[0]:return {'number':18,'state':'open'}
        if '/compare/' in args[0]:return {'status':'identical','merge_base_commit':{'sha':MERGE}}
        if '/check-runs?' in args[0]:return {'total_count':1,'check_runs':[{'id':1,'head_sha':MERGE,'name':'contracts','status':'completed','conclusion':'success'}]}
        raise AssertionError('Unexpected operation '+str(args))

    def test_merged_partial_slice_keeps_unfinished_acceptance_open(self):
        r=self.receipt();out=P.completion(r,REPO,P.Forge(REPO,self.reader),23)
        self.assertFalse(out['assignmentComplete'])
        def closed(args):return {'number':18,'state':'closed'} if '/issues/' in args[0] else self.reader(args)
        with self.assertRaises(P.GateError):P.completion(r,REPO,P.Forge(REPO,closed),23)
        def linked(args):return page([(REPO,18)],merged=True) if args[0]=='graphql' else self.reader(args)
        with self.assertRaises(P.GateError):P.completion(r,REPO,P.Forge(REPO,linked),23)

    def test_final_assignment_needs_all_acceptance_and_live_landing(self):
        r=self.receipt('assignment_complete')
        with self.assertRaises(P.GateError):P.completion(r,REPO)
        r['acceptance'][0].update(complete=True,evidence='Relevant test and independent review passed')
        with self.assertRaises(P.GateError):P.completion(r,REPO)
        result=P.completion(r,REPO,P.Forge(REPO,self.reader),23)
        self.assertTrue(result['assignmentComplete'] and result['landingVerified'])
        for changed in ('queued','failure','missing'):
            def reader(args):
                if '/check-runs?' in args[0]:
                    if changed=='missing':return {'total_count':1,'check_runs':[]}
                    return {'total_count':1,'check_runs':[{'id':1,'head_sha':MERGE,'name':'contracts','status':changed,'conclusion':changed}]}
                return self.reader(args)
            with self.assertRaises(P.GateError):P.completion(r,REPO,P.Forge(REPO,reader),23)

    def test_completed_issue_set_is_read_back_and_cannot_include_unfinished_work(self):
        r=self.receipt('assignment_complete');r['completedIssues']=[REPO+'#18']
        with self.assertRaises(P.GateError):P.completion(r,REPO,P.Forge(REPO,self.reader),23)
        r['acceptance'][0].update(complete=True,evidence='Checked')
        with self.assertRaises(P.GateError):P.completion(r,REPO,P.Forge(REPO,self.reader),23)
        def closed(args):return {'number':18,'state':'closed'} if '/issues/' in args[0] else self.reader(args)
        self.assertTrue(P.completion(r,REPO,P.Forge(REPO,closed),23)['assignmentComplete'])

    def test_statuses_and_repeated_processing_are_read_only(self):
        calls=[]
        def reader(args):calls.append(args);return self.reader(args)
        forge=P.Forge(REPO,reader)
        r=self.receipt();a=P.completion(r,REPO,forge,23);b=P.completion(r,REPO,forge,23)
        self.assertEqual(a,b)
        self.assertTrue(all(args[0]=='graphql' or '/issues/' in args[0] for args in calls))
        for status in ('local_complete','waiting_for_landing','blocked'):
            r=self.receipt(status)
            if status=='blocked':r['blocker']='Waiting for required approval'
            self.assertFalse(P.completion(r,REPO)['assignmentComplete'])
        r=self.receipt('blocked')
        with self.assertRaises(P.GateError):P.completion(r,REPO)
