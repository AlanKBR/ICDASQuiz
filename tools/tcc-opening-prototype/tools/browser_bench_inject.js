(() => {
  if (window.__icdasBench?.cleanup) window.__icdasBench.cleanup();
  const frames = [];
  const longTasks = [];
  const marks = [];
  let previous = 0;
  let active = true;
  let rafId = 0;
  function phase() {
    const raw = document.getElementById('stagePhase')?.textContent || '';
    if (raw.includes('SLIDE 1 · ICDASQUIZ')) return 'titulo_espera';
    if (raw.includes('DESDOBRAMENTO') || raw.includes('CONDENSAÇÃO') || raw.includes('SLIDE 1 → 2')) return 'morph_titulo';
    if (raw.includes('SLIDE 2 · DENTE ASCII')) return 'ascii_espera';
    if (raw.includes('ASCII → MESH')) return 'ascii_mesh';
    if (raw.includes('MESH · ORIENTAÇÃO')) return 'orientacao';
    if (raw.includes('MESH · ENCAIXE')) return 'encaixe';
    if (raw.includes('FOTO · QUIZ')) return 'foto_final';
    if (raw.includes('QUIZ · INTERAÇÃO')) return 'quiz';
    if (raw.includes('CÂMERA · ACENO')) return 'video';
    if (raw.includes('SLIDE · FULLSCREEN')) return 'slide_final';
    return raw.substring(0,40);
  }
  function tick(now) {
    if (!active) return;
    if (previous) {
      const delta = now - previous;
      if (delta > 0 && delta < 500) frames.push({delta:+delta.toFixed(2),phase:phase(),t:Math.round(now)});
    }
    previous = now;
    rafId = requestAnimationFrame(tick);
  }
  try {
    const observer = new PerformanceObserver(list => {
      for (const entry of list.getEntries()) longTasks.push({duration:+entry.duration.toFixed(2),phase:phase()});
    });
    observer.observe({entryTypes:['longtask']});
    window.__icdasBenchObserver = observer;
  } catch (e) {}
  rafId = requestAnimationFrame(tick);
  const gl = document.getElementById('modelCanvas')?.getContext('webgl2');
  const ext=gl?.getExtension('WEBGL_debug_renderer_info');
  const gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null;
  const resource = performance.getEntriesByType('resource').map(x=>({name:x.name.split('/').pop(),duration:Math.round(x.duration),transferSize:x.transferSize,decodedBodySize:x.decodedBodySize}));
  function summarize(){
    const groups={};
    for(const f of frames) (groups[f.phase]??=[]).push(f.delta);
    const results={};
    for(const [label,unsorted] of Object.entries(groups)){
      if(unsorted.length<10)continue;
      const samples=unsorted.slice().sort((a,b)=>a-b);
      const mean=samples.reduce((a,b)=>a+b,0)/samples.length;
      const percentile=p=>samples[Math.min(samples.length-1,Math.ceil(samples.length*p)-1)];
      results[label]={
        frames:samples.length, fps:+(1000/mean).toFixed(1),
        frameMeanMs:+mean.toFixed(2), p95Ms:percentile(.95),
        maxMs:percentile(1),slow33:samples.filter(x=>x>33.3).length,
        longTasks:longTasks.filter(x=>x.phase===label).length
      };
    }
    return {gpu, visible:document.visibilityState, dpr:devicePixelRatio,viewport:[innerWidth,innerHeight],
      phases:results,totalFrames:frames.length,resource, longTasks:longTasks.slice(0,20)};
  }
  window.__icdasBench={frames,longTasks,marks,summarize,cleanup(){active=false;cancelAnimationFrame(rafId);window.__icdasBenchObserver?.disconnect()}};
  return {installed:true,gpu,visible:document.visibilityState,resourceCount:resource.length};
})()
