/* Lightweight gesture controller for the quiz and public image lightboxes.
 * Runs only inside a user-opened modal. Two-finger zoom, one-finger pan when
 * enlarged, keyboard +/-/0, wheel+Ctrl and double-click. No dependencies.
 */
(() => {
  'use strict';
  document.querySelectorAll('[data-pinch-zoom]').forEach(canvas => {
    const img = canvas.querySelector('img');
    if (!img) return;
    const dialog = canvas.closest('dialog');
    const pointers = new Map();
    let scale = 1, x = 0, y = 0, gesture = null;
    const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
    const midpoint = values => ({x: (values[0].x + values[1].x) / 2, y: (values[0].y + values[1].y) / 2});
    const distance = values => Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y) || 1;
    const relative = point => {
      const rect = canvas.getBoundingClientRect();
      return {x:point.x - rect.left - rect.width/2, y:point.y - rect.top - rect.height/2};
    };
    const render = () => {
      if (scale <= 1.01) {scale=1;x=0;y=0;}
      const limitX = canvas.clientWidth * (scale - 1) / 2;
      const limitY = canvas.clientHeight * (scale - 1) / 2;
      x = clamp(x, -limitX, limitX);
      y = clamp(y, -limitY, limitY);
      img.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
      canvas.dataset.zoomScale = scale.toFixed(2);
      canvas.classList.toggle('is-zoomed', scale > 1.01);
    };
    const reset = () => {pointers.clear();gesture=null;scale=1;x=0;y=0;render();};
    const beginGesture = () => {
      if (pointers.size < 2) {gesture=null;return;}
      const points=[...pointers.values()].slice(0,2);
      const center=relative(midpoint(points));
      gesture={distance:distance(points),scale,
        anchorX:(center.x-x)/scale,anchorY:(center.y-y)/scale};
    };
    canvas.addEventListener('pointerdown', event => {
      if (dialog && !dialog.open) return;
      if (event.pointerType !== 'touch' && event.pointerType !== 'pen' && scale <= 1) return;
      pointers.set(event.pointerId, {x:event.clientX,y:event.clientY});
      if (event.pointerType !== 'mouse') {
        try {canvas.setPointerCapture(event.pointerId);} catch (_) { /* ignored */ }
      }
      if (pointers.size === 2) beginGesture();
    });
    canvas.addEventListener('pointermove', event => {
      if (!pointers.has(event.pointerId)) return;
      const previous = pointers.get(event.pointerId);
      pointers.set(event.pointerId, {x:event.clientX,y:event.clientY});
      if (pointers.size >= 2) {
        if (!gesture) beginGesture();
        const points=[...pointers.values()].slice(0,2);
        const center=relative(midpoint(points));
        scale=clamp(gesture.scale * distance(points)/gesture.distance, 1, 4);
        x=center.x-gesture.anchorX*scale;
        y=center.y-gesture.anchorY*scale;
        render();
      } else if (scale > 1 && previous) {
        x+=event.clientX-previous.x;
        y+=event.clientY-previous.y;
        render();
      }
    });
    for (const name of ['pointerup','pointercancel','lostpointercapture']) {
      canvas.addEventListener(name, event => {
        pointers.delete(event.pointerId);
        if (pointers.size < 2) gesture=null;
        render();
      });
    }
    canvas.addEventListener('dblclick', event => {
      event.preventDefault();
      if (scale > 1) reset();
      else {scale=2;render();}
    });
    canvas.addEventListener('keydown', event => {
      if (event.key === '+' || event.key === '=') scale=clamp(scale*1.3,1,4);
      else if (event.key === '-') scale=clamp(scale/1.3,1,4);
      else if (event.key === '0') {reset();event.preventDefault();return;}
      else return;
      event.preventDefault();render();
    });
    canvas.addEventListener('wheel', event => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      scale=clamp(scale*Math.exp(-event.deltaY/180),1,4);
      render();
    }, {passive:false});
    img.addEventListener('load', reset);
    dialog?.addEventListener('close', reset);
    canvas.classList.add('pinch-ready');
    render();
  });
})();
