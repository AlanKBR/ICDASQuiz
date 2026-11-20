// Reproducible Node CPU microbenchmark for the exact glTF geometry.
// Does NOT estimate browser FPS, GPU time or loading over the network.
import * as THREE from 'three';
import { MeshSurfaceSampler } from 'three/addons/math/MeshSurfaceSampler.js';
import { readFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';

const json = JSON.parse(readFileSync(new URL('../public/assets/molar/scene.gltf', import.meta.url),'utf8'));
const buf = readFileSync(new URL('../public/assets/molar/scene.bin', import.meta.url));
const primitive = json.meshes[0].primitives[0];

function attribute(index, componentType, elementSize) {
  const a=json.accessors[index], v=json.bufferViews[a.bufferView];
  if(a.componentType !== componentType) throw Error('Unexpected accessor component type');
  const offset=buf.byteOffset+(v.byteOffset||0)+(a.byteOffset||0);
  const C = componentType===5126 ? Float32Array : Uint32Array;
  return new C(buf.buffer,offset,a.count*elementSize);
}
const geometry=new THREE.BufferGeometry();
geometry.setAttribute('position',new THREE.BufferAttribute(attribute(primitive.attributes.POSITION,5126,3),3));
geometry.setIndex(new THREE.BufferAttribute(attribute(primitive.indices,5125,1),1));
const mesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial());

function oldAreaTraversal(){
  const p=geometry.attributes.position, index=geometry.index;
  const a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3();
  let area=0;
  for(let t=0;t<index.count/3;t++){
    const x=t*3;
    a.fromBufferAttribute(p,index.getX(x));
    b.fromBufferAttribute(p,index.getX(x+1));
    c.fromBufferAttribute(p,index.getX(x+2));
    area+=b.clone().sub(a).cross(c.clone().sub(a)).length()/2;
  }
  return area;
}
function samples(sampler,count=1800){
  const pt=new THREE.Vector3(),n=new THREE.Vector3();
  for(let i=0;i<count;i++)sampler.sample(pt,n);
}
function measured(fn){
  const t=performance.now();fn();return performance.now()-t;
}
const result={meshVertices:geometry.attributes.position.count,meshTriangles:geometry.index.count/3};
const old=[],built=[],sampled=[],resampled=[];
for(let i=0;i<5;i++){
  old.push(measured(oldAreaTraversal));
  let sampler;
  built.push(measured(()=>{sampler=new MeshSurfaceSampler(mesh).build()}));
  sampled.push(measured(()=>samples(sampler)));
  resampled.push(measured(()=>samples(sampler)));
}
const median=values=>values.slice().sort((a,b)=>a-b)[Math.floor(values.length/2)];
result.oldAreaMs=median(old);
result.samplerBuildMs=median(built);
result.sample1800Ms=median(sampled);
result.cachedResample1800Ms=median(resampled);
result.estimatedOldDensityChangeMs=result.oldAreaMs+result.samplerBuildMs+result.sample1800Ms;
result.estimatedOptimizedDensityChangeMs=result.cachedResample1800Ms;
console.log(JSON.stringify(result,null,2));
