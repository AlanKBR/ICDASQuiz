import './style.css';
import './quiz.css';
import './intro.css';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshSurfaceSampler } from 'three/addons/math/MeshSurfaceSampler.js';

const $ = id => document.getElementById(id);
const stage = $('stage');
const presentationMode = new URLSearchParams(location.search).get('presentation') === '1';
if (presentationMode) {
  document.body.classList.add('presentation-mode');
  stage.classList.add('hide-annotations');
}
const canvas = $('modelCanvas');
const monitorBlank = $('monitorBlank');
const monitorQuiz = $('monitorQuiz');
const ambient = $('ambient');
const video = $('introVideo');
const introFinal = $('introFinal');
const durationInput = $('duration');
const densityInput = $('density');
const glyphSizeInput = $('glyphSize');
const quizHoldInput = $('quizHold');
const warmthInput = $('warmStrength');
const rotInputs = [$('rotX'),$('rotY'),$('rotZ')];
const alignInputs = [$('alignX'),$('alignY'),$('alignScale')];
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, +$('renderScale').value));
renderer.setSize(1280, 720, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.35;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 16/9, .1, 100);
camera.position.set(0, 0, 6.0);
camera.lookAt(0,0,0);
scene.add(new THREE.AmbientLight(0xffffff, 1.2));
const keyLight = new THREE.DirectionalLight(0xffffff,3.1);
keyLight.position.set(-3,5,6); scene.add(keyLight);
const rim = new THREE.DirectionalLight(0x65d9cb, 2.4);
rim.position.set(4,-2,-4); scene.add(rim);
const fill = new THREE.DirectionalLight(0xc8e6ff,1.6);
fill.position.set(2,2,2); scene.add(fill);

const pivot = new THREE.Group();
scene.add(pivot);
const sharedReveal = { value: 0 };
const sharedPhotoFade = { value: 0 };
// Approximate the warm cream enamel in the reference photo without replacing
// clinical image pixels or flattening specular details in the 3D surface.
const sharedWarmth = {value:0};
const sharedWarmStrength = {value:+warmthInput.value};
const sharedWarmTint = {value:new THREE.Color('#e6bd96')};
const QUIZ_STEPS = Object.freeze({
  quiet: .13, firstHover: .23, secondHover: .34,
  wrongApproach: .46, wrongClick: .51, wrongEnd: .65,
  rightApproach: .75, rightClick: .82, rightSettle: .90
});
const ASCII_GLYPHS = Array.from('ICDASQuiz0123456@#%&*+=-/?<>[]{}~:');
const ASCII_COLUMNS = 8;
const ASCII_ROWS = Math.ceil(ASCII_GLYPHS.length / ASCII_COLUMNS);
const TITLE_LETTERS = Array.from('ICDASQuiz');
// These timings apply only to the first Next-slide action. The second
// action is deliberately manual, like advancing a slide deck.
const TITLE_HOLD_MS = 800;
const TITLE_UNFOLD_MS = 1400;
const TITLE_CONDENSE_MS = 1600;
const TITLE_MORPH_MS = TITLE_UNFOLD_MS + TITLE_CONDENSE_MS;
const TITLE_TOOTH_HOLD_MS = 450;
const TITLE_TOTAL_MS = TITLE_HOLD_MS + TITLE_MORPH_MS + TITLE_TOOTH_HOLD_MS;
const atlasTexture = makeGlyphAtlas();
let asciiPoints = null;
let modelReady = false;
let meshMaterials = [];
let sampleMeshes = [];
let surfaceSamplers = null;
let surfaceAreas = null;
let surfaceTotalArea = 0;
let modelBounds = new THREE.Box3();
let startQuat = new THREE.Quaternion();
let endQuat = new THREE.Quaternion();
let spinEndQuat = new THREE.Quaternion();
let motionStartTime = 0;
let titleStartTime = 0;
let quizStartedAt = 0;
let quizHoldLength = +quizHoldInput.value * 1000;
const waitingEuler = new THREE.Euler();
const waitingQuat = new THREE.Quaternion();
const titlePivotInverse = new THREE.Matrix4();
let stageMode = 'title';
let paused = false;
let beginTime = 0;
let pauseOffset = 0;
let transitionLength = +durationInput.value;
let sceneProgress = 0;
let lastFrame = performance.now();
let quizNeedsFinalRender = false;
let density = +densityInput.value;
const perfInput=$('perfTelemetry');
const perfSamples=new Float32Array(180);
let perfSamplesSeen=0;
let perfLastUpdate=0;
let perfCpuElapsed=0;
let perfCpuCount=0;
const MORPH_NAMES = ['Magnética','Órbita','Cascata','Dobra espacial'];
// The user picked Spatial Fold as the current design direction. Keep the
// alternative modes available for an immediate A/B comparison.
let morphVariant = 3;
let preferredMorph = -1;
const clamp = (x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const smooth = (a,b,x)=> { const t=clamp((x-a)/(b-a)); return t*t*(3-2*t); };
const easeOutCubic = t => 1-Math.pow(1-clamp(t),3);
const deg = v => +v * Math.PI/180;

function makeGlyphAtlas() {
  const cell=64, c=document.createElement('canvas');
  c.width=cell*ASCII_COLUMNS; c.height=cell*ASCII_ROWS;
  const ctx=c.getContext('2d');
  ctx.fillStyle='white';
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.font='bold 52px monospace';
  ASCII_GLYPHS.forEach((ch,i)=>ctx.fillText(ch,(i%ASCII_COLUMNS)*cell+cell/2,Math.floor(i/ASCII_COLUMNS)*cell+cell/2+3));
  // Collect ink pixels for the nine parent title letters. Spatial Fold's
  // tiny copies will originate from these actual glyph strokes rather than
  // appearing at random points around each letter's bounding box.
  const pixels=ctx.getImageData(0,0,c.width,c.height).data;
  const titleInk=TITLE_LETTERS.map((_,i)=>{
    const candidates=[];
    const ox=(i%ASCII_COLUMNS)*cell;
    const oy=Math.floor(i/ASCII_COLUMNS)*cell;
    for(let py=3;py<cell-3;py+=2){
      for(let px=3;px<cell-3;px+=2){
        const alpha=pixels[((oy+py)*c.width+ox+px)*4+3];
        if(alpha>145)candidates.push([(px+.5)/cell-.5,.5-(py+.5)/cell]);
      }
    }
    return candidates.length?candidates:[[0,0]];
  });
  const texture=new THREE.CanvasTexture(c);
  texture.userData.titleInk=titleInk;
  texture.magFilter=THREE.LinearFilter;
  texture.minFilter=THREE.LinearFilter;
  texture.wrapS=THREE.ClampToEdgeWrapping;
  texture.wrapT=THREE.ClampToEdgeWrapping;
  return texture;
}
function patchReveal(material, geometry) {
  const object = sampleMeshes[sampleMeshes.length-1];
  // Captured before animation: this maps the source mesh into the same
  // pivot-local coordinate system used by the surface-sampled ASCII points.
  const toPivot = object.matrixWorld.clone();
  object.userData.icdasToPivotMatrix=toPivot;
  object.userData.icdasNormalToPivot=new THREE.Matrix3().getNormalMatrix(toPivot);
  // The enamel is always an opaque, front-facing PBR surface.
  // No alpha blending: it allowed deeper/root fragments to show through the crown.
  material.transparent=false;
  material.opacity=1;
  material.side=THREE.FrontSide;
  material.depthWrite=true;
  material.depthTest=true;
  material.onBeforeCompile = shader => {
    shader.uniforms.uReveal=sharedReveal;
    shader.uniforms.uPhotoFade=sharedPhotoFade;
    shader.uniforms.uWarmth=sharedWarmth;
    shader.uniforms.uWarmStrength=sharedWarmStrength;
    shader.uniforms.uWarmTint=sharedWarmTint;
    shader.uniforms.uToPivot={value:toPivot};
    shader.uniforms.uRangeMin={value:modelBounds.min};
    shader.uniforms.uRangeMax={value:modelBounds.max};
    shader.vertexShader='uniform mat4 uToPivot;\nvarying vec3 vToothPosition;\n'+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vToothPosition=(uToPivot*vec4(position,1.0)).xyz;');
    shader.fragmentShader=String.raw`uniform float uReveal;
uniform float uPhotoFade;
uniform float uWarmth;
uniform float uWarmStrength;
uniform vec3 uWarmTint;
uniform vec3 uRangeMin;
uniform vec3 uRangeMax;
varying vec3 vToothPosition;
`+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <clipping_planes_fragment>', String.raw`#include <clipping_planes_fragment>
vec3 normalizedTooth = clamp((vToothPosition-uRangeMin)/max(uRangeMax-uRangeMin,vec3(0.001)),vec3(0.0),vec3(1.0));
float grain = fract(sin(dot(floor(vToothPosition.xyz*19.0),vec3(12.9898,78.233,37.719)))*43758.5453);
float revealCut = clamp(0.10 + normalizedTooth.x*0.75 + normalizedTooth.z*0.08 + (grain-0.5)*0.07,0.02,0.97);
if (uReveal < revealCut) discard;
// Screen-door dissolve keeps every surviving fragment solid and depth-writing.
float photoDither = fract(sin(dot(floor(gl_FragCoord.xy),vec2(12.9898,78.233)))*43758.5453);
if (uPhotoFade > photoDither) discard;
`);
    // Apply a warm enamel colour cast after tone mapping, before conversion
    // to display RGB. Preserve original pixel luminance for cusps, gloss and
    // crevices instead of flattening the 3D surface into a uniform beige.
    shader.fragmentShader=shader.fragmentShader.replace('#include <tonemapping_fragment>',String.raw`#include <tonemapping_fragment>
float enamelLuma=dot(gl_FragColor.rgb,vec3(0.2126,0.7152,0.0722));
float targetLuma=max(dot(uWarmTint,vec3(0.2126,0.7152,0.0722)),0.001);
vec3 gradedEnamel=clamp(uWarmTint*(enamelLuma/targetLuma),vec3(0.0),vec3(1.0));
gl_FragColor.rgb=mix(gl_FragColor.rgb,gradedEnamel,clamp(uWarmth*uWarmStrength,0.0,0.85));
`);
  };
  material.customProgramCacheKey=()=> 'icdas-tooth-opaque-reveal-v4-warmth';
}
function createAscii(points, seed, glyph, order, titleIndices, heroFlags, birthOffsets) {
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
  geometry.setAttribute('aSeed',new THREE.Float32BufferAttribute(seed,1));
  geometry.setAttribute('aGlyph',new THREE.Float32BufferAttribute(glyph,1));
  geometry.setAttribute('aOrder',new THREE.Float32BufferAttribute(order,1));
  geometry.setAttribute('aTitleIndex',new THREE.Float32BufferAttribute(titleIndices,1));
  geometry.setAttribute('aHero',new THREE.Float32BufferAttribute(heroFlags,1));
  geometry.setAttribute('aBirthOffset',new THREE.Float32BufferAttribute(birthOffsets,2));
  const uniforms={
    uAtlas:{value:atlasTexture},
    uProgress:{value:0},
    uTime:{value:0},
    uOpacity:{value:1.0},
    uGlyphSize:{value:+glyphSizeInput.value},
    uTitleProgress:{value:0},
    uMorphVariant:{value:morphVariant},
    uFoldGhostAlpha:{value:+$('foldGhostAlpha').value},
    uTitleSpacing:{value:.23},
    uTitleZ:{value:2.2},
    uHeroGlyphSize:{value:62},
    uInversePivot:{value:new THREE.Matrix3()},
    uAccent:{value:new THREE.Color('#adfff0')}
  };
  const material=new THREE.ShaderMaterial({
    uniforms,transparent:true,depthWrite:false,depthTest:true,
    blending:THREE.NormalBlending,
    vertexShader:String.raw`attribute float aSeed;
attribute float aGlyph;
attribute float aOrder;
attribute float aTitleIndex;
attribute float aHero;
attribute vec2 aBirthOffset;
uniform float uProgress;
uniform float uTime;
uniform float uOpacity;
uniform float uGlyphSize;
uniform float uTitleProgress;
uniform float uMorphVariant;
uniform float uFoldGhostAlpha;
uniform float uTitleSpacing;
uniform float uTitleZ;
uniform float uHeroGlyphSize;
uniform mat3 uInversePivot;
varying float vGlyph;
varying float vAlpha;
varying float vTitleMix;
varying float vQuizSource;
varying float vUnfold;
void main(){
  float unfolding=smoothstep(0.01,0.4667,uTitleProgress);
  float condensation=smoothstep(0.4667,1.0,uTitleProgress);
  // ICDAS and Quiz retain their original, readable identity until the
  // letters have populated the small halo around the title.
  vGlyph=mix(aTitleIndex,aGlyph,step(0.997,uTitleProgress));
  vTitleMix=1.0-smoothstep(0.48,1.0,uTitleProgress);
  vQuizSource=step(4.5,aTitleIndex);
  vUnfold=unfolding;
  float stagger = aOrder;
  float peeled = smoothstep(stagger-.035,stagger+.045,uProgress);
  // Copies appear over time and remain airy while they are close to the
  // typography. They gain full opacity only as they occupy the molar.
  float copyArrival=smoothstep(0.02+aSeed*.23,0.29+aSeed*.22,uTitleProgress);
  if(uMorphVariant>1.5 && uMorphVariant<2.5){
    // Cascade: each letter releases its copies in readable left-to-right order.
    copyArrival=smoothstep(.09+aTitleIndex*.043,.25+aTitleIndex*.043,uTitleProgress);
  }
  float copyOpacity=mix(0.40,1.0,condensation)*copyArrival;
  if(uMorphVariant>2.5){
    // Fold: copies are born nearly invisible at their OWN source glyph,
    // stay translucent while the typographic sheet unfolds, and become
    // opaque only as they settle into the finished ASCII molar.
    float departure=smoothstep(.08+aSeed*.10,.25+aSeed*.11,uTitleProgress);
    float settling=smoothstep(.72,.998,uTitleProgress);
    copyOpacity=departure*mix(uFoldGhostAlpha,1.0,settling);
  }
  vAlpha=(1.0-peeled)*uOpacity*mix(copyOpacity,1.0,aHero);
  // Title anchors are fixed in camera space, even while the molar rotates.
  vec3 titleWorld=vec3((aTitleIndex-4.0)*uTitleSpacing,0.0,uTitleZ);
  vec3 titleLocal=uInversePivot*titleWorld;
  // All four choreographies preserve the same typography and the same glTF
  // target positions. Only the path between them changes.
  float fanAngle=aSeed*6.2831853+aTitleIndex*.17;
  float move=smoothstep(.43+aSeed*.09,.995,uTitleProgress);
  float heroMove=smoothstep(.62,1.0,uTitleProgress);
  float t=mix(move,heroMove,aHero);
  vec3 p=titleLocal;
  if(uMorphVariant<.5){
    // 01 MAGNETIC: the restrained V0.8 baseline.
    vec3 haloOffset=vec3(
      cos(fanAngle)*(.11+aSeed*.15),
      sin(fanAngle)*(.10+aSeed*.16),
      -.10-aSeed*.12
    );
    vec3 spread=mix(titleLocal,titleLocal+uInversePivot*haloOffset,unfolding*(1.0-aHero));
    p=mix(spread,position,t);
    float arc=sin(t*3.14159265);
    p.y+=arc*(aSeed-.5)*.19*(1.0-aHero*.35);
    p.z+=arc*.17;
  } else if(uMorphVariant<1.5){
    // 02 ORBITAL: copies trace revolving ellipses in depth before settling.
    float orbitAngle=fanAngle+unfolding*3.4+condensation*3.2;
    float radius=(.25+aSeed*.34)*unfolding*(1.0-aHero);
    vec3 orbitalOffset=vec3(
      cos(orbitAngle)*radius,
      sin(orbitAngle)*radius*.78,
      (-.14-aSeed*.25)*unfolding*(1.0-aHero)
    );
    vec3 orbitPoint=titleLocal+uInversePivot*orbitalOffset;
    p=mix(orbitPoint,position,t);
    float orbitTrail=sin(t*3.14159265)*(1.0-aHero);
    p.x+=cos(orbitAngle+2.3)*.27*orbitTrail;
    p.y+=sin(orbitAngle+2.3)*.24*orbitTrail;
    p.z+=orbitTrail*.24;
  } else if(uMorphVariant<2.5){
    // 03 CASCADE: a choreographed wave from I to z, with upright ribbons.
    float columnDelay=aTitleIndex*.042;
    float wave=smoothstep(.32+columnDelay,.83+columnDelay,uTitleProgress);
    float heroWave=smoothstep(.65,1.0,uTitleProgress);
    t=mix(wave,heroWave,aHero);
    vec3 ribbon=uInversePivot*vec3(
      (aSeed-.5)*.18,
      (.16+aSeed*.49)*unfolding,
      -.13*unfolding
    );
    vec3 source=titleLocal+ribbon*(1.0-aHero);
    p=mix(source,position,t);
    float lift=sin(t*3.14159265);
    p.y+=lift*(.26+aSeed*.24);
    p.z+=lift*.12;
    p.x+=lift*(aSeed-.5)*.14;
  } else {
    // 04 SPATIAL FOLD, revised: each tiny glyph visibly emerges FROM
    // its parent character, fans out locally, and then joins a gently
    // folded typographic sheet. Do not spawn particles across the scene.
    float departure=smoothstep(.085+aSeed*.08,.265+aSeed*.09,uTitleProgress);
    float sheetFormation=smoothstep(.22,.46,uTitleProgress);
    float angle=fanAngle+aOrder*1.1;
    vec3 inkPoint=titleLocal+uInversePivot*vec3(
      aBirthOffset.x*uTitleSpacing*.94,
      aBirthOffset.y*uTitleSpacing*.94,
      -.018
    );
    vec3 emitterOffset=uInversePivot*vec3(
      cos(angle)*(.09+aSeed*.13),
      sin(angle)*(.07+aSeed*.11),
      -.055-aSeed*.085
    );
    vec3 nearParent=inkPoint+emitterOffset;
    vec3 sheetOffset=uInversePivot*vec3(
      (aSeed-.5)*.54,
      (aOrder-.5)*1.12,
      -.20+sin(angle)*.10
    );
    vec3 localFan=mix(inkPoint,nearParent,departure);
    vec3 sheet=mix(localFan,titleLocal+sheetOffset,sheetFormation);
    sheet=mix(titleLocal,sheet,1.0-aHero);
    float fold=smoothstep(.48+aSeed*.08,.995,uTitleProgress);
    t=mix(fold,heroMove,aHero);
    p=mix(sheet,position,t);
    float foldArc=sin(t*3.14159265);
    p.z+=foldArc*(.21+.11*aSeed);
    p.x+=foldArc*sin(angle)*.075;
  }
  vec4 mvPosition=modelViewMatrix*vec4(p,1.0);
  gl_Position=projectionMatrix*mvPosition;
  float toothSize=min(72.0,(uGlyphSize+aSeed*4.0)*6.0/-mvPosition.z);
  float smallGlyphFactor=uMorphVariant>2.5 ? .29 : .44;
  float titleSize=mix(uHeroGlyphSize*smallGlyphFactor,uHeroGlyphSize,aHero);
  gl_PointSize=mix(titleSize,toothSize,smoothstep(.48,.985,uTitleProgress));
}`,
    fragmentShader:String.raw`uniform sampler2D uAtlas;
uniform vec3 uAccent;
uniform float uTime;
uniform float uTitleProgress;
varying float vGlyph;
varying float vAlpha;
varying float vTitleMix;
varying float vQuizSource;
varying float vUnfold;
void main(){
  if(vAlpha<0.005) discard;
  float column=mod(vGlyph,8.0);
  float row=floor(vGlyph/8.0);
  vec2 uv=vec2((column+gl_PointCoord.x)/8.0,(5.0-row-gl_PointCoord.y)/5.0);
  float mask=texture2D(uAtlas,uv).a;
  if(mask<0.035) discard;
  // The Quiz half of the title breathes between two restrained teal/mint
  // shades. ICDAS stays stable, almost white. The mint gradually travels
  // into the emerging tooth before all glyphs return to their common tone.
  float breathing=.5+.5*sin(uTime*1.7);
  vec3 offWhite=vec3(.90,.95,.985);
  vec3 quizMint=mix(vec3(.29,.75,.66),vec3(.58,.98,.83),breathing);
  vec3 titleTone=mix(offWhite,quizMint,vQuizSource);
  float inheritedMint=vQuizSource*.42*vUnfold*(1.0-smoothstep(.76,1.0,uTitleProgress));
  vec3 toothTone=mix(uAccent,quizMint,inheritedMint);
  vec3 tone=mix(toothTone,titleTone,vTitleMix);
  float luminous=mix(1.0,1.04+.06*breathing,vQuizSource*vTitleMix);
  gl_FragColor=vec4(min(tone*luminous,vec3(1.0)),mask*vAlpha*.89);
}`
  });
  const cloud=new THREE.Points(geometry,material);
  cloud.frustumCulled=false;
  cloud.renderOrder=10;
  return cloud;
}
function setText(id,v){
  const el=$(id);
  // Timers only change a few times per second. Avoid forcing DOM mutations
  // on every requestAnimationFrame while keeping displayed data identical.
  if(el.textContent!==String(v))el.textContent=v;
}
function updateTitleGeometry(){
  if(!asciiPoints) return;
  const r=stage.getBoundingClientRect();
  const physicalScale=renderer.getPixelRatio();
  const heroPx=Math.min(68,Math.max(22,r.width*.052));
  const worldHeight=2*Math.tan(THREE.MathUtils.degToRad(camera.fov)/2)*(camera.position.z-2.2);
  const worldPerPixel=worldHeight/Math.max(1,r.height);
  asciiPoints.material.uniforms.uTitleSpacing.value=heroPx*1.1*worldPerPixel;
  asciiPoints.material.uniforms.uHeroGlyphSize.value=heroPx*physicalScale;
  // Invert the pivot rotation to prevent the title from tilting with the tooth.
  titlePivotInverse.makeRotationFromQuaternion(pivot.quaternion).invert();
  asciiPoints.material.uniforms.uInversePivot.value.setFromMatrix4(titlePivotInverse);
}
// Percent coordinates are measured from the original 1672x941 quiz reference.
// The pointer approaches 5, passes over 2, tests 3, and then selects 4.
// Each beat is normalized by the adjustable quiz-hold duration.
const QUIZ_POINTER_PATH=[
  {at:0,x:69,y:74},
  {at:QUIZ_STEPS.quiet,x:69,y:74},
  {at:QUIZ_STEPS.firstHover,x:60.12,y:59.87},
  {at:.28,x:60.12,y:59.87},
  {at:.36,x:45.03,y:59.87},
  {at:.40,x:45.03,y:59.87},
  {at:.47,x:50.08,y:59.87},
  {at:QUIZ_STEPS.wrongEnd,x:50.08,y:59.87},
  {at:QUIZ_STEPS.rightApproach,x:55.06,y:59.87},
  {at:1,x:55.06,y:59.87}
];
function quizCursorAt(p){
  for(let i=1;i<QUIZ_POINTER_PATH.length;i++){
    const b=QUIZ_POINTER_PATH[i],a=QUIZ_POINTER_PATH[i-1];
    if(p>b.at)continue;
    const eased=smooth(a.at,b.at,p);
    return {x:a.x+(b.x-a.x)*eased,y:a.y+(b.y-a.y)*eased};
  }
  return {x:55.06,y:59.87};
}
function clearQuizInteraction(){
  stage.classList.remove('quiz-active','quiz-clicked','quiz-wrong-active','quiz-hover-on');
  const mouse=$('quizMouse');
  mouse.style.opacity='0';
  mouse.style.left='69%';mouse.style.top='74%';
  $('quizHover').style.opacity='0';
}
function updateQuizInteraction(elapsed){
  const p=clamp(elapsed/quizHoldLength);
  const cursor=quizCursorAt(p);
  const mouse=$('quizMouse');
  mouse.style.left=cursor.x.toFixed(3)+'%';
  mouse.style.top=cursor.y.toFixed(3)+'%';
  mouse.style.opacity=p>=QUIZ_STEPS.quiet && p<QUIZ_STEPS.rightSettle ? '1':'0';

  const wrong=p>=QUIZ_STEPS.wrongClick && p<QUIZ_STEPS.wrongEnd;
  const success=p>=QUIZ_STEPS.rightClick;
  stage.classList.toggle('quiz-wrong-active',wrong);
  stage.classList.toggle('quiz-clicked',success);
  const hoverNumber=
    p>=.20 && p<.28 ? 5 :
    p>=.34 && p<.40 ? 2 :
    p>=.46 && p<QUIZ_STEPS.wrongClick ? 3 :
    p>=QUIZ_STEPS.rightApproach && p<QUIZ_STEPS.rightClick ? 4 : null;
  stage.classList.toggle('quiz-hover-on',hoverNumber!==null);
  const hover=$('quizHover');
  if(hoverNumber!==null){
    hover.style.left=({2:45.03,3:50.08,4:55.06,5:60.12})[hoverNumber]+'%';
    hover.style.top='59.87%';
    hover.style.opacity='';
  }
  if(p<QUIZ_STEPS.quiet) setText('status','Quiz demonstrativo · pausa para observação');
  else if(wrong) setText('status','Quiz demonstrativo · tentativa no 3');
  else if(p>=QUIZ_STEPS.wrongEnd && !success) setText('status','Quiz demonstrativo · tentando outra opção');
  else if(success) setText('status','Quiz demonstrativo · opção 4 selecionada');
  else setText('status','Quiz demonstrativo · explorando os códigos');
}
function outputQuaternion() {
  return new THREE.Quaternion().setFromEuler(new THREE.Euler(deg(rotInputs[0].value),deg(rotInputs[1].value),deg(rotInputs[2].value),'XYZ'));
}
// This is the actual idle spin. Playback uses the SAME function and phase,
// so clicking Start never begins a second, faster rotational animation.
function waitingQuaternionAt(time, target=waitingQuat) {
  waitingEuler.set(
    -.65+Math.sin(time*.00044)*.18,
    time*.00027,
    .32+Math.cos(time*.00034)*.07,
    'XYZ'
  );
  return target.setFromEuler(waitingEuler);
}
function samplePoints() {
  if (!modelReady) return;
  if (asciiPoints) {
    pivot.remove(asciiPoints);
    asciiPoints.geometry.dispose(); asciiPoints.material.dispose();
  }
  const coords=new Float32Array(density*3);
  const seeds=new Float32Array(density);
  const glyphs=new Float32Array(density);
  const orders=new Float32Array(density);
  const titleIndices=new Float32Array(density);
  const heroFlags=new Float32Array(density);
  const birthOffsets=new Float32Array(density*2);
  const point=new THREE.Vector3();
  const normal=new THREE.Vector3();
  // Reuse the sampler's triangle distribution across density changes.
  // This model has exactly one mesh: skip the old redundant 57,008-triangle
  // area traversal altogether. Keep multi-mesh weighting as a fallback.
  if(!surfaceSamplers){
    surfaceSamplers=sampleMeshes.map(m=>new MeshSurfaceSampler(m).build());
    if(sampleMeshes.length===1){
      surfaceAreas=[1];
      surfaceTotalArea=1;
    }else{
      surfaceAreas=sampleMeshes.map(m=>{
        const geo=m.geometry,p=geo.attributes.position,i=geo.index;
        const a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3();
        const ab=new THREE.Vector3(),ac=new THREE.Vector3();
        let area=0;
        const triCount=i?i.count/3:p.count/3;
        for(let t=0;t<triCount;t++){
          const ix=t*3;
          a.fromBufferAttribute(p,i?i.getX(ix):ix);
          b.fromBufferAttribute(p,i?i.getX(ix+1):ix+1);
          c.fromBufferAttribute(p,i?i.getX(ix+2):ix+2);
          area+=ab.subVectors(b,a).cross(ac.subVectors(c,a)).length()*.5;
        }
        return area;
      });
      surfaceTotalArea=surfaceAreas.reduce((a,b)=>a+b,0);
    }
  }
  for(let i=0;i<density;i++){
    let idx=0;
    if(surfaceAreas.length>1){
      let choice=Math.random()*surfaceTotalArea;
      while(idx<surfaceAreas.length-1 && choice>surfaceAreas[idx])choice-=surfaceAreas[idx++];
    }
    const mesh=sampleMeshes[idx];
    surfaceSamplers[idx].sample(point,normal);
    // matrixWorld changes every frame when the pivot rotates. Reusing it here
    // would double-rotate newly sampled characters after a density adjustment.
    point.applyMatrix4(mesh.userData.icdasToPivotMatrix);
    const nX=clamp((point.x-modelBounds.min.x)/Math.max(.001,modelBounds.max.x-modelBounds.min.x));
    const nZ=clamp((point.z-modelBounds.min.z)/Math.max(.001,modelBounds.max.z-modelBounds.min.z));
    const grainInput=Math.floor(point.x*19)*12.9898
      +Math.floor(point.y*19)*78.233+Math.floor(point.z*19)*37.719;
    const noise=Math.sin(grainInput)*43758.5453;
    const grain=noise-Math.floor(noise);
    // Same spatial reveal function as the textured mesh; both are registered
    // against the same original model, before adding a tiny normal offset.
    orders[i]=clamp(.10+nX*.75+nZ*.08+(grain-.5)*.07,.02,.97);
    normal.applyMatrix3(mesh.userData.icdasNormalToPivot).normalize();
    point.addScaledVector(normal,.018);
    coords[i*3]=point.x;coords[i*3+1]=point.y;coords[i*3+2]=point.z;
    // The final ASCII molar is built exclusively from the nine letters
    // of ICDASQuiz, matching the source typography of the first slide.
    // Keep the larger atlas for compatibility with all four morph shaders.
    seeds[i]=Math.random(); glyphs[i]=Math.floor(Math.random()*TITLE_LETTERS.length);
    const parentIndex=i%TITLE_LETTERS.length;
    titleIndices[i]=parentIndex;
    heroFlags[i]=i<TITLE_LETTERS.length?1:0;
    const ink=atlasTexture.userData.titleInk[parentIndex];
    const [birthX,birthY]=ink[Math.floor(Math.random()*ink.length)];
    birthOffsets[i*2]=birthX;birthOffsets[i*2+1]=birthY;
  }
  asciiPoints=createAscii(coords,seeds,glyphs,orders,titleIndices,heroFlags,birthOffsets);
  pivot.add(asciiPoints);
  asciiPoints.material.uniforms.uTitleProgress.value=stageMode==='title'?0:1;
  updateTitleGeometry();
}
async function loadTooth(){
 try {
  const gltf=await new GLTFLoader().loadAsync('./assets/molar/scene.gltf');
  const loaded=gltf.scene;
  const b=new THREE.Box3().setFromObject(loaded);
  const size=b.getSize(new THREE.Vector3());
  const center=b.getCenter(new THREE.Vector3());
  const scale=2.8/Math.max(size.x,size.y,size.z);
  loaded.scale.multiplyScalar(scale);
  loaded.position.copy(center).multiplyScalar(-scale);
  pivot.add(loaded);
  loaded.updateMatrixWorld(true);
  // The bounding box is measured once in pivot-local space and shared by
  // the ASCII character positions and the textured mesh reveal shader.
  modelBounds.copy(new THREE.Box3().setFromObject(loaded));
  const originals=[];
  loaded.traverse(obj=>{if(obj.isMesh) originals.push(obj)});
  originals.forEach(obj=>{
      const clone=obj.material.clone();
      obj.material=clone;
      sampleMeshes.push(obj);
      patchReveal(clone,obj.geometry);
      meshMaterials.push(clone);
      // Render an invisible solid surface into the depth buffer. It prevents
      // back-side ASCII (and roots) from bleeding through the crown even while
      // the textured surface is only partially revealed.
      const depthMat=new THREE.MeshDepthMaterial({side:THREE.FrontSide});
      depthMat.colorWrite=false;
      depthMat.depthWrite=true;
      depthMat.polygonOffset=true;
      depthMat.polygonOffsetFactor=1;
      depthMat.polygonOffsetUnits=1;
      const depthOccluder=new THREE.Mesh(obj.geometry,depthMat);
      depthOccluder.renderOrder=-10;
      depthOccluder.frustumCulled=false;
      obj.add(depthOccluder);
  });
  if (!sampleMeshes.length) throw Error('Modelo não contém malha');
  modelReady=true;
  samplePoints();
  setText('status','Modelo carregado · pronto');
  $('loading').classList.add('hidden');
  $('play').disabled=false;$('reset').disabled=false;
  $('previewMorph').disabled=false;
  $('previewQuiz').disabled=false;
  reset();
 } catch(err) {
  setText('status','Erro ao carregar o molar');
  $('loading').textContent='Erro ao carregar a geometria: '+err.message;
  console.error(err);
 }
}
function reset(){
  video.pause(); video.currentTime=0;
  video.style.opacity='0';
  introFinal.style.opacity='0';
  canvas.style.opacity='1';
  stageMode='title';paused=false; sceneProgress=0;
  monitorBlank.style.opacity='0';monitorQuiz.style.opacity='0';ambient.style.opacity='1';
  sharedReveal.value=0;
  sharedPhotoFade.value=0;
  sharedWarmth.value=0;
  quizNeedsFinalRender=false;
  pivot.position.set(0,0,0);
  pivot.scale.setScalar(1);
  pivot.quaternion.copy(waitingQuaternionAt(performance.now()));
  if(asciiPoints) {
    asciiPoints.material.uniforms.uTitleProgress.value=0;
    asciiPoints.material.uniforms.uMorphVariant.value=morphVariant;
  }
  $('titleAura').style.opacity='1';
  clearQuizInteraction();
  stage.classList.add('is-advanceable');
  $('pause').disabled=true; $('pause').textContent='Pausar';
  $('play').disabled=!modelReady;
  $('play').textContent='Próximo: formar dente ▶';
  setText('stagePhase','SLIDE 1 · ICDASQUIZ');
  $('timelineFill').style.width='0%';
  setText('timeReadout','Aguardando 1º avanço');
  setText('status','Título pronto · próximo slide');
  notifyPresentationPhase('title');
}
function notifyPresentationPhase(phase){
  // The agent's slide deck can embed this build on the same origin and drive
  // it using postMessage. A standalone window remains fully interactive.
  if(!presentationMode || window.parent===window)return;
  window.parent.postMessage({source:'icdasquiz-opening',event:'phase',phase},location.origin);
}
function beginTitle(){
  if(!modelReady || stageMode!=='title')return;
  titleStartTime=performance.now();
  stageMode='forming';
  stage.classList.remove('is-advanceable');
  setText('stagePhase','SLIDE 1 → 2 · FORMAÇÃO');
  setText('status','Formando dente ASCII');
  $('play').disabled=true;
  notifyPresentationPhase('forming');
}
function beginMesh(now){
  if(!modelReady || stageMode!=='asciiReady')return;
  motionStartTime=now;
  startQuat.copy(waitingQuaternionAt(now));
  endQuat.copy(outputQuaternion());
  spinEndQuat.copy(waitingQuaternionAt(now+transitionLength*700));
  stageMode='playing';
  stage.classList.remove('is-advanceable');
  beginTime=now;pauseOffset=0;
  $('titleAura').style.opacity='0';
  if(asciiPoints) asciiPoints.material.uniforms.uTitleProgress.value=1;
  $('pause').disabled=false;paused=false;
  $('play').disabled=true;
  setText('status','Animação 3D em andamento');
  setText('stagePhase','SLIDE 2 → INTRODUÇÃO');
  notifyPresentationPhase('mesh');
}
function advanceSlide(){
  if(!modelReady)return;
  if(stageMode==='title') beginTitle();
  else if(stageMode==='asciiReady') beginMesh(performance.now());
}
function playExistingVideo(){
  if(!modelReady)return;
  video.pause();
  video.currentTime=0;
  stageMode='video';
  video.style.opacity='0';
  introFinal.style.opacity='0';
  setText('stagePhase','CÂMERA · ACENO');
  setText('status','Vídeo de 4 segundos');
  // Switch only when the first decoded frame is ready. That first frame is
  // now an exact copy of the selected quiz state, so there is no blank gap.
  const reveal = () => {
    if(stageMode!=='video')return;
    video.style.opacity='1';
    canvas.style.opacity='0';
  };
  if(video.seeking) video.addEventListener('seeked',reveal,{once:true});
  else if(video.readyState>=2) reveal();
  else video.addEventListener('loadeddata',reveal,{once:true});
  const promise=video.play();
  if (promise) promise.catch(err=>{setText('status','Não foi possível reproduzir vídeo');console.error(err)});
}
video.addEventListener('transitionend',event=>{
  if(event.propertyName==='opacity' && stageMode==='video' && video.style.opacity==='1')
    clearQuizInteraction();
});
video.addEventListener('ended',()=>{
  stageMode='finished';
  introFinal.style.opacity='1';
  video.style.opacity='0';
  setText('stagePhase','SLIDE · FULLSCREEN');
  setText('status','Fim da abertura');
  $('timelineFill').style.width='100%';
  setText('timeReadout','Concluído');
  notifyPresentationPhase('finished');
});
function updatePhase(p){
  // A tooth stays centred while ASCII progressively becomes a fully solid
  // anatomical mesh. Keep spinning throughout this entire transformation.
  // Only AFTER the reveal and occlusal turn are complete may it shrink/move.
  const reveal=smooth(.035,.70,p);
  sharedReveal.value=reveal;
  sharedWarmth.value=smooth(.78,.965,p);
  const monitor=smooth(.82,.94,p);
  monitorBlank.style.opacity=monitor.toFixed(3);
  monitorQuiz.style.opacity=smooth(.91,.99,p).toFixed(3);
  ambient.style.opacity=(1-monitor).toFixed(3);
  // A short, decisive ease-out resembles the pace of the camera rotation,
  // without the previous slow vertical drift. The tooth only moves after
  // the occlusal orientation has settled.
  const alignment=easeOutCubic((p-.84)/.095);
  pivot.position.x=(+alignInputs[0].value||0)*alignment;
  pivot.position.y=(+alignInputs[1].value||0)*alignment;
  const scale=1- (1-(+alignInputs[2].value||.78))*alignment;
  pivot.scale.setScalar(scale);
  if(p<=.70){
    pivot.quaternion.copy(waitingQuaternionAt(motionStartTime + p*transitionLength*1000));
  } else {
    spinEndQuat.copy(waitingQuaternionAt(motionStartTime + .70*transitionLength*1000));
    pivot.quaternion.copy(spinEndQuat).slerp(endQuat,smooth(.70,.84,p));
  }
  if(asciiPoints){
    asciiPoints.material.uniforms.uProgress.value=reveal;
    asciiPoints.material.uniforms.uOpacity.value=1;
  }
  // Dithered discard rather than transparent PBR materials: surviving
  // enamel pixels retain full opacity and correct depth sorting.
  sharedPhotoFade.value=smooth(.94,1,p);
  if($('debugOverlap').checked){
    sharedReveal.value=1;
    sharedPhotoFade.value=0;
    if(asciiPoints){
      asciiPoints.material.uniforms.uProgress.value=0;
      asciiPoints.material.uniforms.uOpacity.value=.75;
    }
  }
  const phases=p<.70?'ASCII → MESH · GIRO':p<.84?'MESH · ORIENTAÇÃO OCLUSAL':p<.94?'MESH · ENCAIXE':'FOTO · QUIZ';
  setText('stagePhase',phases);
  setText('status',phases);
  setText('timeReadout', (p*transitionLength).toFixed(1)+' s / '+transitionLength.toFixed(1)+' s');
  const whole=TITLE_TOTAL_MS/1000+transitionLength+quizHoldLength/1000+4;
  $('timelineFill').style.width=((TITLE_TOTAL_MS/1000+p*transitionLength)/whole*100).toFixed(2)+'%';
}
function resize() {
  const r=stage.getBoundingClientRect(), w=Math.max(100,Math.round(r.width)),h=Math.max(100,Math.round(r.height));
  renderer.setSize(w,h,false);
  camera.aspect=w/h;camera.updateProjectionMatrix();
  updateTitleGeometry();
}
$('renderScale').addEventListener('change',()=>{
  const ratio=+($('renderScale').value);
  renderer.setPixelRatio(Math.min(devicePixelRatio,ratio));
  resize();
  perfSamplesSeen=0;
  setText('status','Resolução de prévia: '+renderer.getPixelRatio().toFixed(2)+'×');
});
perfInput.addEventListener('change',()=>{
  $('perfMetrics').hidden=!perfInput.checked;
  perfSamplesSeen=0;
  perfCpuElapsed=0;perfCpuCount=0;perfLastUpdate=0;
});
function recordPerf(now,frameMs,cpuRenderMs){
  if(!perfInput.checked)return;
  if(frameMs>0 && frameMs<150){
    perfSamples[perfSamplesSeen%perfSamples.length]=frameMs;
    perfSamplesSeen++;
  }
  perfCpuElapsed+=cpuRenderMs;
  perfCpuCount++;
  if(now-perfLastUpdate<1500 || perfSamplesSeen<15)return;
  const len=Math.min(perfSamplesSeen,perfSamples.length);
  const samples=Array.from(perfSamples.slice(0,len)).sort((a,b)=>a-b);
  const mean=samples.reduce((a,b)=>a+b,0)/len;
  const p95=samples[Math.min(len-1,Math.ceil(len*.95)-1)];
  setText('perfFps',Math.round(1000/mean).toString());
  setText('perfP95',p95.toFixed(1)+' ms');
  setText('perfCpu',(perfCpuElapsed/Math.max(1,perfCpuCount)).toFixed(2)+' ms');
  setText('perfDraws',renderer.info.render.calls.toString());
  setText('perfTriangles',renderer.info.render.triangles.toLocaleString('pt-BR'));
  setText('perfTextures',renderer.info.memory.textures.toString());
  perfLastUpdate=now;
  perfCpuElapsed=0;perfCpuCount=0;
}
const observer=new ResizeObserver(resize);observer.observe(stage);
resize();
function animate(now){
  requestAnimationFrame(animate);
  const frameMs=now-lastFrame;
  lastFrame=now;
  if(stageMode==='title' && modelReady){
    pivot.quaternion.copy(waitingQuaternionAt(now));
    pivot.scale.setScalar(1);
    pivot.position.set(0,0,0);
    sharedReveal.value=0;sharedPhotoFade.value=0;
    if(asciiPoints){
      asciiPoints.material.uniforms.uProgress.value=0;
      asciiPoints.material.uniforms.uOpacity.value=1;
      asciiPoints.material.uniforms.uTitleProgress.value=0;
    }
    updateTitleGeometry();
  } else if(stageMode==='forming' && modelReady){
    const elapsed=now-titleStartTime;
    // Each phase owns its easing in the vertex shader. Use linear overall
    // progress to preserve the intended 1.4 s unfold / 1.6 s condensation.
    const formation=clamp((elapsed-TITLE_HOLD_MS)/TITLE_MORPH_MS);
    pivot.quaternion.copy(waitingQuaternionAt(now));
    pivot.position.set(0,0,0);
    pivot.scale.setScalar(1);
    sharedReveal.value=0;sharedPhotoFade.value=0;
    if(asciiPoints){
      asciiPoints.material.uniforms.uTitleProgress.value=formation;
      asciiPoints.material.uniforms.uProgress.value=0;
      asciiPoints.material.uniforms.uOpacity.value=1;
    }
    updateTitleGeometry();
    $('titleAura').style.opacity=String(1-smooth(.15,.72,formation));
    const whole=TITLE_TOTAL_MS/1000+transitionLength+quizHoldLength/1000+4;
    $('timelineFill').style.width=(Math.min(elapsed,TITLE_TOTAL_MS)/1000/whole*100).toFixed(2)+'%';
    setText('stagePhase',
      elapsed < TITLE_HOLD_MS ? 'SLIDE 1 → 2 · TÍTULO' :
      elapsed < TITLE_HOLD_MS+TITLE_UNFOLD_MS ? 'SLIDE 1 → 2 · DESDOBRAMENTO' :
      elapsed < TITLE_HOLD_MS+TITLE_MORPH_MS ? 'SLIDE 1 → 2 · CONDENSAÇÃO' :
      'SLIDE 1 → 2 · DENTE ASCII'
    );
    setText('timeReadout','Título → ASCII · '+(Math.min(elapsed,TITLE_TOTAL_MS)/1000).toFixed(1)+' s');
    if(elapsed>=TITLE_TOTAL_MS){
      stageMode='asciiReady';
      notifyPresentationPhase('asciiReady');
      stage.classList.add('is-advanceable');
      if(asciiPoints) asciiPoints.material.uniforms.uTitleProgress.value=1;
      $('titleAura').style.opacity='0';
      $('play').disabled=false;
      $('play').textContent='Próximo: iniciar animação ▶';
      setText('status','Dente ASCII pronto · aguardando 2º avanço');
      setText('stagePhase','SLIDE 2 · DENTE ASCII');
      setText('timeReadout','Aguardando 2º avanço');
    }
  } else if(stageMode==='asciiReady' && modelReady){
    // The completed ASCII molar keeps its original idle rotation until
    // the second manual Next-slide action.
    pivot.quaternion.copy(waitingQuaternionAt(now));
    pivot.scale.setScalar(1);
    pivot.position.x=0;
    pivot.position.y=0;
    sharedReveal.value=0;
    sharedPhotoFade.value=0;
    if(asciiPoints){
      asciiPoints.material.uniforms.uTitleProgress.value=1;
      asciiPoints.material.uniforms.uProgress.value=0;
      asciiPoints.material.uniforms.uOpacity.value=1;
    }
  }else if(stageMode==='playing' && !paused) {
    sceneProgress=clamp((now-beginTime-pauseOffset)/(transitionLength*1000));
    updatePhase(sceneProgress);
    if(sceneProgress>=1){
      stageMode='quizHold';
      quizNeedsFinalRender=true;
      quizStartedAt=now;
      stage.classList.add('quiz-active');
      updateQuizInteraction(0);
      setText('stagePhase','QUIZ · INTERAÇÃO SIMULADA');
      $('pause').disabled=true;
    }
  } else if(stageMode==='quizHold') {
    const elapsed=now-quizStartedAt;
    updateQuizInteraction(elapsed);
    setText('timeReadout','Quiz · '+Math.min(quizHoldLength/1000,elapsed/1000).toFixed(1)+' s');
    const progress=(TITLE_TOTAL_MS/1000+transitionLength+Math.min(quizHoldLength,elapsed)/1000)/(TITLE_TOTAL_MS/1000+transitionLength+quizHoldLength/1000+4);
    $('timelineFill').style.width=(progress*100).toFixed(2)+'%';
    if(elapsed>=quizHoldLength){
      stageMode='quizStill';
      setText('status','Quiz · demonstração concluída');
      if($('autoplay').checked) playExistingVideo();
    }
  }
  // The existing video/final slide already cover the canvas. Avoid issuing
  // invisible WebGL draws while the browser decodes the video, or while a
  // static slide is being shown.
  if(stageMode==='video'||stageMode==='finished'||stageMode==='quizStill'||document.hidden)return;
  if(stageMode==='quizHold' && !quizNeedsFinalRender)return;
  if(asciiPoints) asciiPoints.material.uniforms.uTime.value=now*.001;
  const start=performance.now();
  renderer.render(scene,camera);
  if(stageMode==='quizHold')quizNeedsFinalRender=false;
  recordPerf(now,frameMs,performance.now()-start);
}
requestAnimationFrame(animate);
function refreshMorphControls() {
  document.querySelectorAll('[data-morph-variant]').forEach(button=>{
    const index=Number(button.dataset.morphVariant);
    const chosen=index===morphVariant;
    button.classList.toggle('is-selected',chosen);
    button.classList.toggle('is-preferred',index===preferredMorph);
    button.setAttribute('aria-pressed',String(chosen));
  });
  const preferred=preferredMorph===morphVariant;
  $('foldAdjustments').hidden=morphVariant!==3;
  $('markPreferred').textContent=preferred?'Preferida neste navegador ✓':'Marcar como preferida';
  $('morphFeedback').textContent=preferred
    ? MORPH_NAMES[morphVariant]+' está marcada como sua preferida neste navegador. Informe o nome para aprovação definitiva.'
    : 'Selecionada: '+MORPH_NAMES[morphVariant]+'. Clique em “Testar transformação” para ver só o primeiro avanço.';
}
function selectMorphVariant(index) {
  if(!Number.isInteger(index)||index<0||index>=MORPH_NAMES.length)return;
  morphVariant=index;
  // Keep the same surface samples for a fair A/B comparison. Switching
  // during the second animation returns safely to the title scene.
  if(asciiPoints)asciiPoints.material.uniforms.uMorphVariant.value=morphVariant;
  if(modelReady)reset();
  refreshMorphControls();
}
document.querySelectorAll('[data-morph-variant]').forEach(button=>{
  button.addEventListener('click',()=>selectMorphVariant(Number(button.dataset.morphVariant)));
});
$('foldGhostAlpha').addEventListener('input',()=>{
  const amount=+$('foldGhostAlpha').value;
  $('foldGhostVal').textContent=Math.round(amount*100)+'%';
  if(asciiPoints)asciiPoints.material.uniforms.uFoldGhostAlpha.value=amount;
});
$('previewMorph').addEventListener('click',()=>{
  if(!modelReady)return;
  reset();
  beginTitle(); // Ends at the ASCII tooth and waits; never runs the full video.
  refreshMorphControls();
});
$('markPreferred').addEventListener('click',()=>{
  preferredMorph=morphVariant;
  try { localStorage.setItem('icdasquiz-preferred-morph-v09',String(preferredMorph)); }
  catch { /* preference is optional; visual testing must work without storage */ }
  refreshMorphControls();
});
try {
  const stored=localStorage.getItem('icdasquiz-preferred-morph-v09');
  const index=stored===null?-1:Number(stored);
  if(Number.isInteger(index)&&index>=0&&index<MORPH_NAMES.length) {
    preferredMorph=index;
    morphVariant=index;
  }
} catch { /* file-mode/private browsers may disable storage */ }
refreshMorphControls();
$('play').addEventListener('click',advanceSlide);
window.addEventListener('message',event=>{
  if(!presentationMode || event.source!==window.parent || event.origin!==location.origin)return;
  if(event.data?.source!=='icdasquiz-presentation-controller')return;
  if(event.data.action==='next')advanceSlide();
  else if(event.data.action==='reset')reset();
  else if(event.data.action==='getState')notifyPresentationPhase(stageMode);
});
$('stage').addEventListener('click',()=>{
  if(stageMode==='title'||stageMode==='asciiReady')advanceSlide();
});
document.addEventListener('keydown',event=>{
  if(event.defaultPrevented || event.repeat || event.altKey || event.ctrlKey || event.metaKey)return;
  if(!['ArrowRight','PageDown',' ','Enter'].includes(event.key))return;
  if(event.target.closest?.('input,textarea,select,[contenteditable="true"]'))return;
  if(event.target.closest?.('.morph-options'))return;
  // Enter/Space on a focused button already invokes its native click.
  if((event.key==='Enter'||event.key===' ') && event.target.closest?.('button'))return;
  if(stageMode!=='title'&&stageMode!=='asciiReady')return;
  event.preventDefault();
  advanceSlide();
});
$('reset').addEventListener('click',reset);
$('previewClip').addEventListener('click',playExistingVideo);
$('previewQuiz').addEventListener('click',()=>{
  if(!modelReady)return;
  // Start with the textured model already revealed, just before its final
  // occlusal orientation / warm colour grade. This avoids replaying the
  // title and entire ASCII metamorphosis during design reviews.
  reset();
  const previewProgress=.73;
  const now=performance.now();
  motionStartTime=now-previewProgress*transitionLength*1000;
  beginTime=motionStartTime;
  pauseOffset=0;paused=false;
  endQuat.copy(outputQuaternion());
  spinEndQuat.copy(waitingQuaternionAt(motionStartTime+.70*transitionLength*1000));
  stageMode='playing';
  stage.classList.remove('is-advanceable');
  $('titleAura').style.opacity='0';
  if(asciiPoints)asciiPoints.material.uniforms.uTitleProgress.value=1;
  $('play').disabled=true;
  $('pause').disabled=false;
  updatePhase(previewProgress);
  setText('status','Prévia do modelo 3D → fotografia → quiz');
});
$('pause').addEventListener('click',()=>{
  if(stageMode!=='playing')return;
  paused=!paused;
  if(paused){pauseOffset=performance.now()-beginTime-pauseOffset; $('pause').textContent='Retomar';}
  else{beginTime=performance.now()-pauseOffset;pauseOffset=0;$('pause').textContent='Pausar';}
});
const scrub=$('scrub');
scrub.addEventListener('input',()=>{
  if(!modelReady)return;
  paused=true;
  stageMode='scrub';
  video.pause();
  clearQuizInteraction();
  video.style.opacity='0';introFinal.style.opacity='0';
  canvas.style.opacity='1';
  if(!motionStartTime) motionStartTime=performance.now();
  startQuat.copy(waitingQuaternionAt(motionStartTime));
  if(asciiPoints) asciiPoints.material.uniforms.uTitleProgress.value=1;
  $('titleAura').style.opacity='0';
  endQuat.copy(outputQuaternion());
  spinEndQuat.copy(waitingQuaternionAt(motionStartTime+transitionLength*700));
  const p=+scrub.value/100;
  $('scrubValue').textContent=Math.round(p*100)+'%';
  updatePhase(p);
  setText('status','Inspeção de sobreposição · '+Math.round(p*100)+'%');
});
function refreshScrub(){
  if(stageMode==='scrub')updatePhase(+scrub.value/100);
}
rotInputs.concat(alignInputs).forEach(el=>el.addEventListener('input',refreshScrub));
$('debugOverlap').addEventListener('change',refreshScrub);
durationInput.addEventListener('input',()=>{
  transitionLength=+durationInput.value;
  setText('durationVal',String(transitionLength).replace('.',',')+' s');
});
quizHoldInput.addEventListener('input',()=>{
  quizHoldLength=+quizHoldInput.value*1000;
  setText('quizHoldVal',String(quizHoldLength/1000).replace('.',',')+' s');
});
warmthInput.addEventListener('input',()=>{
  sharedWarmStrength.value=+warmthInput.value;
  setText('warmStrengthVal',Math.round(sharedWarmStrength.value*100)+'%');
  if(stageMode==='scrub')updatePhase(+scrub.value/100);
});
densityInput.addEventListener('input',()=>{
  density=+densityInput.value;
  setText('densityVal',String(density));
});
densityInput.addEventListener('change',()=>{if(stageMode==='title'||stageMode==='asciiReady')samplePoints();});
glyphSizeInput.addEventListener('input',()=>{
  const size=+glyphSizeInput.value;
  setText('glyphSizeVal',size+' px');
  if(asciiPoints) asciiPoints.material.uniforms.uGlyphSize.value=size;
});
$('showAnnotations').addEventListener('change',e=>stage.classList.toggle('hide-annotations',!e.target.checked));
$('copySettings').addEventListener('click',()=>{
  const txt=JSON.stringify({
    model:'Maxillary First Molar (Dundee Dental) CC BY 4.0',
    titleMorph:{variant:morphVariant,name:MORPH_NAMES[morphVariant],preferred:preferredMorph===morphVariant,foldGhostOpacity:+$('foldGhostAlpha').value},
    asciiPointCount:density,asciiGlyphSizePx:+glyphSizeInput.value,transitionDurationSeconds:transitionLength,
    occlusalRotationDegrees:rotInputs.map(x=>+x.value),
    photoAlignment:{x:+alignInputs[0].value,y:+alignInputs[1].value,scale:+alignInputs[2].value},
    quizHoldSeconds:quizHoldLength/1000,simulatedQuizSelection:4,
    autoContinueVideo:$('autoplay').checked,
    handoff:'docs/TCC_ABERTURA_3D_HANDOFF_20261117.md'
  },null,2);
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    navigator.clipboard.writeText(txt)
      .then(()=>setText('status','Parâmetros copiados'))
      .catch(()=>{setText('status','Falha ao copiar; veja o console');console.info(txt);});
  } else {
    const temp=document.createElement('textarea');
    temp.value=txt;temp.style.position='fixed';temp.style.opacity='0';
    document.body.append(temp);temp.select();
    const copied=document.execCommand('copy');
    temp.remove();
    setText('status',copied?'Parâmetros copiados':'Parâmetros no console');
    if(!copied)console.info(txt);
  }
});
loadTooth();
