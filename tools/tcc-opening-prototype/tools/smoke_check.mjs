// Lightweight offline regression checks for the consolidated opening.
// Complements (but does not replace) a visual WebGL test on the Legion.
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { join } from 'node:path';

const root=new URL('../',import.meta.url).pathname;
const read=p=>readFileSync(join(root,p));
const src=read('src/main.js').toString('utf8');
const html=read('index.html').toString('utf8');
const gltf=JSON.parse(read('public/assets/molar/scene.gltf').toString());
const fragment=(s,label)=>assert.ok(src.includes(s),'Missing '+label);
const noFragment=(s,label)=>assert.ok(!src.includes(s),'Regression '+label);

assert.match(html,/V0\.10\.1/);
fragment("const TITLE_LETTERS = Array.from('ICDASQuiz')",'title');
fragment('glyphs[i]=Math.floor(Math.random()*TITLE_LETTERS.length)','nine ASCII glyphs');
fragment("else if(stageMode==='asciiReady') beginMesh(performance.now())",'two advances');
noFragment('if(elapsed>=TITLE_TOTAL_MS) beginMesh(now)','automatic second advance');
fragment('stageMode===\'asciiReady\' && modelReady','idle molar');
fragment('uWarmTint','photo colour grade');
fragment("stage.classList.toggle('quiz-wrong-active',wrong)",'quiz red shake');
fragment("stage.classList.toggle('quiz-clicked',success)",'quiz green check');
fragment("const QUIZ_POINTER_PATH=",'quiz cursor path');
fragment("if(!surfaceSamplers){",'sampler cache');
fragment("if(stageMode==='video'||stageMode==='finished'||stageMode==='quizStill'||document.hidden)return;",'skip invisible WebGL');
fragment("const perfInput=$('perfTelemetry');",'opt-in telemetry');
fragment("renderer.setPixelRatio(Math.min(devicePixelRatio,ratio))",'adjustable resolution');
noFragment('updateAsciiVisibility','rejected ASCII grid');

for(const id of ['perfTelemetry','renderScale','perfFps','perfP95','perfCpu','perfDraws','perfTriangles','perfTextures']){
 assert.ok(html.includes('id="'+id+'"'),'missing performance UI '+id);
}
const glyphs=Array.from('ICDASQuiz');
assert.equal(glyphs.length,9);
assert.equal(gltf.meshes.length,1);
const primitive=gltf.meshes[0].primitives[0];
assert.equal(gltf.accessors[primitive.attributes.POSITION].count,28875);
assert.equal(gltf.accessors[primitive.indices].count/3,57008);

for(const tex of ['defaultMat_baseColor.png','defaultMat_normal.png']){
 const bytes=read('public/assets/molar/textures/'+tex);
 assert.equal(bytes.subarray(1,4).toString(),'PNG','PNG signature '+tex);
 assert.equal(bytes.readUInt32BE(16),2048,'PNG width '+tex);
 assert.equal(bytes.readUInt32BE(20),2048,'PNG height '+tex);
}
for(const redundant of [
 'dist/assets/intro_video_raw_4s.mp4',
 'dist/assets/intro_video_4s_v05.mp4',
 'dist/assets/occlusal_clinical_original.png',
 'dist/assets/monitor_intro_reference.png'
])assert.equal(existsSync(join(root,redundant)),false,'private redundant asset '+redundant);
for(const essential of ['dist/assets/intro_video_4s.mp4','dist/assets/monitor_quiz_reference.png','dist/assets/molar/scene.bin']){
 assert.equal(existsSync(join(root,essential)),true,'essential asset '+essential);
}
for(const file of ['dist/index.html','dist/assets/molar/scene.bin']){
 assert.deepEqual(gunzipSync(read(file+'.gz')),read(file),'gzip integrity '+file);
}
console.log('PASS: 2 manual advances, nine ASCII glyphs, photo grade, quiz story, sampler cache, perf UI, original geometry, 2K textures, private assets and gzip integrity.');
