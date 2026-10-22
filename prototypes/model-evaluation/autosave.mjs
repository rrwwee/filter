// One in-flight request. Replace queued work with the newest complete snapshot.
export function createAutosaver({persist, status}) {
  let pending = null, running = null, version = 0;
  async function drain() {
    while (pending) {
      const job = pending; pending = null;
      try {
        await persist(job.snapshot);
        if (job.version === version) status('Saved locally.');
      } catch (error) {
        if (job.version === version) status('Save failed: ' + error.message);
      }
    }
  }
  function start() {
    running = drain().finally(() => {
      running = null;
      if (pending) return start();
    });
    return running;
  }
  return {
    enqueue(snapshot) {
      pending = {snapshot: structuredClone(snapshot), version: ++version};
      status('Saving…');
      if (!running) start();
      return running;
    },
    flush() { return running || Promise.resolve(); },
  };
}
