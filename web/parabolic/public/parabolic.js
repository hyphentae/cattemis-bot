function range(min,max,step) {
  if (min == null) return [];
  if (max == null) {
    if (min > 0) return Array.from({length: min}, (_,i) => i);
    return Array.from({length: -min}, (_,i) => -i);
  }
  if (step == null) {
    if (max > min) return Array.from({length: max-min+1}, (_,i) => min + i);
    return Array.from({length: min-max+1}, (_,i) => min - i);
  }
  if (max > min) return Array.from({length: (max-min)/step+1}, (_,i) => min + i*step);
  return Array.from({length: (max-min)/step+1}, (_,i) => min - i*step);
}

var sqrt = Math.sqrt;
var sign = Math.sign;

var Parabolic = (sigma,rho) => [sigma*rho,.5*(sigma*sigma-rho*rho)]

var toParabolic = (x,y) => {
  var root = sqrt(x*x + y*y);
  var sigma = sqrt(root + y);
  var rho = sqrt(root - y);
  return [sigma,rho];
}

p = range(8,0).flatMap(y => range(-8,8).map(x => Parabolic(x,y)))

A = [0,17,34,51,68,85,102,119,136,135,118,101,84,67,50,33,16].map(i => p[i]);
B = [1,18,35,52,69,86,103,120,137,134,117,100,83,66,49,32,15].map(i => p[i]);
C = [2,19,36,53,70,87,104,121,138,133,116,99,82,65,48,31,14].map(i => p[i]);
D = [3,20,37,54,71,88,105,122,139,132,115,98,81,64,47,30,13].map(i => p[i]);
E = [4,21,38,55,72,89,106,123,140,131,114,97,80,63,46,29,12].map(i => p[i]);
F = [5,22,39,56,73,90,107,124,141,130,113,96,79,62,45,28,11].map(i => p[i]);
G = [6,23,40,57,74,91,108,125,142,129,112,95,78,61,44,27,10].map(i => p[i]);
H = [7,24,41,58,75,92,109,126,143,128,111,94,77,60,43,26,9].map(i => p[i]);

Q0= [8,25,42,59,76,93,110,127,144,127,110,93,76,59,42,25,8].map(i => p[i]);

I = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16].map(i => p[i]);
J = [17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33].map(i => p[i]);
K = [34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50].map(i => p[i]);
L = [51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67].map(i => p[i]);
M = [68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84].map(i => p[i]);
N = [85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101].map(i => p[i]);
O = [102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118].map(i => p[i]);
P = [119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135].map(i => p[i]);

Q1= [136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152].map(i => p[i]);

fA = x => -x*x/128 + 32;
fB = x => -x*x/98 + 24.5;
fC = x => -x*x/72 + 18;
fD = x => -x*x/50 + 12.5;
fE = x => -x*x/32 + 8;
fF = x => -x*x/18 + 4.5;
fG = x => -x*x/8 + 2;
fH = x => -x*x/2 + 0.5;

mp = (f,a,x0,x2) => [
  (x0 + x2)/2,
  (f(x0) + f(x2) - a*(x2 - x0)**2)/2,
];

A1 = A.slice(1).map((p,i) => mp(fA,-1/128,p[0],A[i][0]));
B1 = B.slice(1).map((p,i) => mp(fB,-1/98,p[0],B[i][0]));
C1 = C.slice(1).map((p,i) => mp(fC,-1/72,p[0],C[i][0]));
D1 = D.slice(1).map((p,i) => mp(fD,-1/50,p[0],D[i][0]));
E1 = E.slice(1).map((p,i) => mp(fE,-1/32,p[0],E[i][0]));
F1 = F.slice(1).map((p,i) => mp(fF,-1/18,p[0],F[i][0]));
G1 = G.slice(1).map((p,i) => mp(fG,-1/8,p[0],G[i][0]));
H1 = H.slice(1).map((p,i) => mp(fH,-1/2,p[0],H[i][0]));

I1 = A1.map(p => [p[0],-p[1]]);
J1 = B1.map(p => [p[0],-p[1]]);
K1 = C1.map(p => [p[0],-p[1]]);
L1 = D1.map(p => [p[0],-p[1]]);
M1 = E1.map(p => [p[0],-p[1]]);
N1 = F1.map(p => [p[0],-p[1]]);
O1 = G1.map(p => [p[0],-p[1]]);
P1 = H1.map(p => [p[0],-p[1]]);

AH = (i,j) => [A,B,C,D,E,F,G,H,Q0][i][j];
AH1 = (i,j) => [A1,B1,C1,D1,E1,F1,G1,H1,Q0][i][j];
IP = (i,j) => [I,J,K,L,M,N,O,P,Q1][i][j];
IP1 = (i,j) => [I1,J1,K1,L1,M1,N1,O1,P1,Q1][i][j];

var canvas = document.createElement('canvas');
var ctx = canvas.getContext('2d');
document.body.appendChild(canvas);

var s;

var mouse = {};
mouse.id = null;

function updateMouse(event) {
  var rect = canvas.getBoundingClientRect();
  var x = event.clientX - rect.left;
  var y = event.clientY - rect.top;
  x = x * 80/s - 40;
  y = -(y * 80/s - 40);
  if (window.myColor === 'black') {
    x *= -1;
    y *= -1;
  }
  var [sig,rho] = toParabolic(x,y);
  mouse.id = (8-sig) << 3 | (8-rho) | ((x > 0) << 6);
  mouse._sig = Math.floor(sig);
  mouse._rho = Math.floor(rho);
  mouse.x = x;
  mouse.y = y;
  mouse.sig = sig;
  mouse.rho = rho;
}

canvas.onpointermove = function(event) {
  if (event.isPrimary === false) return;
  updateMouse(event);
  onMouseMove();
}

canvas.onpointerdown = function(event) {
  if (event.isPrimary === false) return;
  this.setPointerCapture(event.pointerId);
  updateMouse(event);
  onMouseDown();
}

canvas.onpointerup = function(event) {
  if (event.isPrimary === false) return;
  this.releasePointerCapture(event.pointerId);
  updateMouse(event);
  onMouseUp();
}

canvas.onpointercancel = function(event) {
  if (event.isPrimary === false) return;
  onMouseUp();
};

function pfromid(id) {
  return [8 - (id >> 3 & 7), 8 - (id & 7)];
}

function resize() {
  s = Math.min(window.innerHeight, window.innerWidth);
  canvas.width = canvas.height = s;
}

resize();

window.onresize = resize;

function moveTo(x,y) {
  y = 40 - y;
  var r = s / 40;
  x *= r; y *= r;
  ctx.moveTo(x,y);
}
function lineTo(x,y) {
  y = 40 - y;
  var r = s / 40;
  x *= r; y *= r;
  ctx.lineTo(x,y);
}
function drawLine(x0,y0,x1,y1) {
  y0 = 40 - y0
  y1 = 40 - y1;
  var r = s / 40;
  x0 *= r; y0 *= r;
  x1 *= r; y1 *= r;
  ctx.moveTo(x0,y0);
  ctx.lineTo(x1,y1);
}

function bezTo(cx,cy,x1,y1) {
  cy = 40 - cy;
  y1 = 40 - y1;
  var r = s / 40;
  cx *= r; cy *= r;
  x1 *= r; y1 *= r;
  ctx.quadraticCurveTo(cx,cy,x1,y1);
}

function drawBez(x0,y0,cx,cy,x1,y1) {
  y0 = 40 - y0;
  cy = 40 - cy;
  y1 = 40 - y1;
  var r = s / 40;
  x0 *= r; y0 *= r;
  cx *= r; cy *= r;
  x1 *= r; y1 *= r;
  ctx.moveTo(x0,y0);
  ctx.quadraticCurveTo(cx,cy,x1,y1);
}

function fillText(text,x,y) {
  y = 40 - y;
  var r = s / 40;
  x *= r; y *= r;
  ctx.fillText(text,x,y);
}

function drawImage(img,sig,rho,flip,ax) {
var [x,y] = Parabolic(sig,rho);
var w = img.width;
var h = img.height;
if (flip) x *= -1;
var phi = ax ? Math.atan(-x/sig/sig)
             : Math.atan(x/rho/rho);
var scl = Math.sqrt(sig*sig + rho*rho) * s/80;
x += 40; window.ass =  Math.sqrt(sig*sig + rho*rho);
y *= -1;
y += 40;
x *= s/80;
y *= s/80;
  ctx.save();

  ctx.translate(x,y);
  ctx.rotate(-phi);

  ctx.drawImage(img,-scl/2,-scl/2, scl, scl);

  ctx.restore();
}

bx = range(8).map(j => range(8).map(i => [
  AH(j,i),
  AH1(j,i),
  IP(i+1,j),
  IP(i+1,j+1),
  AH(j+1,i+1),
  AH1(j+1,i),
  IP(i,j+1),
  IP1(i,j),
])).flat();

bxx = bx.map(b => b.map(b => [b[0]/2 + 20, b[1]/2+20]));
nxx = bx.map(b => b.map(b => [-b[0]/2 + 20, b[1]/2+20]));

db = bxx.map(bx => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
drawBez(b0,b1,b2,b3,b4,b5);
bezTo(b6,b7,b8,b9);
bezTo(b10,b11,b12,b13);
bezTo(b14,b15,b0,b1);
}});

nb = nxx.map(bx => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
drawBez(b0,b1,b2,b3,b4,b5);
bezTo(b6,b7,b8,b9);
bezTo(b10,b11,b12,b13);
bezTo(b14,b15,b0,b1);
}});

bb = db.concat(nb);

tdb = bxx.map((bx,i) => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
fillText(i,
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
}});

tnb = nxx.map((bx,i) => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
fillText(i,
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
}});

ctx.lineCap = 'round';

tdc = bxx.map((bx,i) => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
ctx.lineWidth = Math.max(Math.abs(b6 - b0),Math.abs(b7-b1))*s/80;
ctx.beginPath();
moveTo(
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
lineTo(
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
ctx.stroke();
ctx.lineWidth = 1;
ctx.closePath();
}});

tnc = nxx.map((bx,i) => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
ctx.lineWidth = Math.max(Math.abs(b6 - b0),Math.abs(b7-b1))*s/80;
ctx.beginPath();
moveTo(
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
lineTo(
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
ctx.stroke();
ctx.lineWidth = 1;
ctx.closePath();
}});

cc = tdc.concat(tnc);
tbb = bxx.concat(nxx).map((bx,i) => {
var [b0,b1,b2,b3,b4,b5,
  b6,b7,b8,b9,b10,b11,
  b12,b13,b14,b15] = bx.flat();
return function() {
fillText(i,
  (b0+b4+b8+b12)/4,
  (b1+b5+b9+b13)/4,
);
}});

excludedSquares = [
  0,1,2,3,8,9,10,11,16,17,18,19,24,25,26,27,
  64,65,66,67,72,73,74,75,80,81,82,83,88,89,90,91,
];

rookLines = [[
  [/*0,1,2,3,*/4,5,6,7,71,70,69,68/*,67,66,65,64*/],
  [/*8,9,10,11,*/12,13,14,15,79,78,77,76/*,75,74,73,72*/],
  [/*16,17,18,19,*/20,21,22,23,87,86,85,84/*,83,82,81,80*/],
  [/*24,25,26,27,*/28,29,30,31,95,94,93,92/*,91,90,89,88*/],
  [32,33,34,35,36,37,38,39,103,102,101,100,99,98,97,96],
  [40,41,42,43,44,45,46,47,111,110,109,108,107,106,105,104],
  [48,49,50,51,52,53,54,55,119,118,117,116,115,114,113,112],
  [56,57,58,59,60,61,62,63,127,126,125,124,123,122,121,120],
],[
  [/*0,8,16,24,*/32,40,48,56,120,112,104,96/*,88,80,72,64*/],
  [/*1,9,17,25,*/33,41,49,57,121,113,105,97/*,89,81,73,65*/],
  [/*2,10,18,26,*/34,42,50,58,122,114,106,98/*,90,82,74,66*/],
  [/*3,11,19,27,*/35,43,51,59,123,115,107,99/*,91,83,75,67*/],
  [4,12,20,28,36,44,52,60,124,116,108,100,92,84,76,68],
  [5,13,21,29,37,45,53,61,125,117,109,101,93,85,77,69],
  [6,14,22,30,38,46,54,62,126,118,110,102,94,86,78,70],
  [7,15,23,31,39,47,55,63,127,119,111,103,95,87,79,71],
]];

bishopLines = [[
  /*[1,8],
  [2,9,16],
  [3,10,17,24],
  [4,11,18,25,32],*/
  [5,12],[33,40],
  [6,13,20],[34,41,48],
  [7,14,21,28,35,42,49,56],
  [71,15,22,29,36,43,50,57,120],
  [70,79,23,30,37,44,51,58,121,112],
  [69,78,87,31,38,45,52,59,122,113,104],
  [68,77,86,95,39,46,53,60,123,114,105,96],
  [76,85,94,103,47,54,61,124,115,106,97],
  [84,93,102,111,55,62,125,116,107,98],
  [92,101,110,119,63,126,117,108,99],
  [100,109,118,127,55,46,37,28],
  [100,109,118,127,62,53,44,35],
],[
  [69,76],[97,104],
  [70,77,84],[98,105,112],
  [71,78,85,92,99,106,113,120],
  [7,79,86,93,100,107,114,121,56],
  [6,15,87,94,101,108,115,122,57,48],
  [5,14,23,95,102,109,116,123,58,49,40],
  [4,13,22,31,103,110,117,124,59,50,41,32],
  [12,21,30,39,111,118,125,60,51,42,33],
  [20,29,38,47,119,126,61,52,43,34],
  [28,37,46,55,127,62,53,44,35],
  [36,45,54,63,119,110,101,92],
  [36,45,54,63,126,117,108,99],
]];

knightOffsets = [[],[],[],[],[14,21],[15,20,22],[12,79,21,23],[13,78,22,87],[],[],[],[],[6,22,29],[7,23,28,30],[4,20,87,71,29,31],[5,21,86,70,30,95],[],[],[],[],[14,30,5,35,37],[15,31,4,6,36,38],[12,28,95,79,5,7,37,39],[13,29,94,78,6,71,38,103],[],[],[],[],[22,38,13,43,45],[23,39,12,14,44,46,35],[20,36,103,87,13,15,45,47],[21,37,102,86,14,79,46,111],[42,49],[43,48,50],[40,28,44,49,51],[41,29,45,50,52],[42,30,46,21,51,53],[43,31,47,20,22,52,54],[28,44,111,95,21,23,53,55],[29,45,110,94,22,87,54,119],[34,50,57],[35,51,56,58],[32,48,36,52,57,59],[33,49,37,53,58,60,28],[34,50,38,54,29,59,61],[35,51,39,55,28,30,60,62],[36,52,119,103,29,31,61,63],[37,53,118,102,30,95,62,127],[42,58,33,121],[43,59,32,34,122,120],[40,56,44,60,33,35,123,121],[41,57,45,61,34,36,124,122],[42,58,46,62,35,37,125,123],[43,59,47,63,36,38,126,124],[44,60,127,111,37,39,127,125],[45,61,126,110,38,103,63,126],[50,122,41,113],[51,123,40,42,114,112],[48,120,52,124,41,43,115,113],[49,121,53,125,42,44,116,114],[50,122,54,126,43,45,117,115],[51,123,55,127,44,46,118,116],[52,124,63,119,45,47,119,117],[53,125,62,118,46,111,55,118],[],[],[],[],[78,85],[79,86,84],[15,76,87,85],[14,77,23,86],[],[],[],[],[86,70,93],[87,71,94,92],[7,23,84,68,95,93],[6,22,85,69,31,94],[],[],[],[],[94,78,101,99,69],[95,79,102,100,70,68],[15,31,92,76,103,101,71,69],[14,30,93,77,39,102,7,70],[],[],[],[],[102,86,109,107,77],[103,87,110,108,78,76,99],[23,39,100,84,111,109,79,77],[22,38,101,85,47,110,15,78],[106,113],[107,114,112],[108,92,104,115,113],[109,93,105,116,114],[110,94,106,117,115,85],[111,95,107,118,116,86,84],[31,47,108,92,119,117,87,85],[30,46,109,93,55,118,23,86],[114,98,121],[115,99,122,120],[116,100,112,96,123,121],[117,101,113,97,124,122,92],[118,102,114,98,125,123,93],[119,103,115,99,126,124,94,92],[39,55,116,100,127,125,95,93],[38,54,117,101,63,126,31,94],[122,106,57,97],[123,107,56,58,98,96],[124,108,120,104,57,59,99,97],[125,109,121,105,58,60,100,98],[126,110,122,106,59,61,101,99],[127,111,123,107,60,62,102,100],[47,63,124,108,61,63,103,101],[46,62,125,109,62,127,39,102],[58,114,49,105],[59,115,48,50,106,104],[60,116,56,112,49,51,107,105],[61,117,57,113,50,52,108,106],[62,118,58,114,51,53,109,107],[63,119,59,115,52,54,110,108],[55,127,60,116,53,55,111,109],[54,126,61,117,54,119,47,110]];

kingOffsets = [[],[],[],[],[5,12,13],[4,6,13,12,14],[5,7,14,13,15],[6,71,15,14,79],[],[],[],[],[13,4,20,5,21],[12,14,5,21,6,20,4,22],[13,15,6,22,7,21,5,23],[14,79,7,23,71,22,6,87],[],[],[],[],[21,12,28,13,29],[20,22,13,29,14,28,12,30],[21,23,14,30,15,29,13,31],[22,87,15,31,79,30,14,95],[],[],[],[],[29,20,36,21,35,37],[28,30,21,37,22,36,20,38],[29,31,22,38,23,37,21,39],[30,95,23,39,87,38,22,103],[33,40,41],[32,34,41,40,42],[33,35,42,41,43],[34,36,43,28,42,44],[35,37,28,44,29,43,45],[36,38,29,45,30,44,46,28],[37,39,30,46,31,45,29,47],[38,103,31,47,95,46,30,111],[41,32,48,33,49],[40,42,33,49,34,48,50,32],[41,43,34,50,35,49,51,33],[42,44,35,51,36,50,52,34],[43,45,36,52,37,51,53,35],[44,46,37,53,38,52,36,54],[45,47,38,54,39,53,55,37],[46,111,39,55,103,54,38,119],[49,40,56,41,57],[48,50,41,57,42,56,58,40],[49,51,42,58,43,57,59,41],[50,52,43,59,44,58,60,42],[51,53,44,60,45,59,61,43],[52,54,45,61,46,60,62,44],[53,55,46,62,47,61,45,63],[54,119,47,63,111,62,127,46],[57,48,120,49,121],[56,58,49,121,50,120,122,48],[57,59,50,122,51,121,123,49],[58,60,51,123,52,122,124,50],[59,61,52,124,53,123,125,51],[60,62,53,125,54,124,126,52],[61,63,54,126,55,125,127,53],[62,127,55,119,126,54],[],[],[],[],[69,76,77],[70,68,77,78,76],[71,69,78,79,77],[7,70,79,15,78],[],[],[],[],[77,84,68,85,69],[78,76,85,69,68,86,70,84],[79,77,86,70,69,87,71,85],[15,78,87,71,70,23,7,86],[],[],[],[],[85,92,76,93,77],[86,84,93,77,76,94,78,92],[87,85,94,78,77,95,79,93],[23,86,95,79,78,31,15,94],[],[],[],[],[93,100,84,101,85,99],[94,92,101,85,84,102,86,100],[95,93,102,86,85,103,87,101],[31,94,103,87,86,39,23,102],[97,104,105],[98,96,105,106,104],[99,97,106,107,105],[100,98,107,108,92,106],[101,99,108,92,109,93,107],[102,100,109,93,92,110,94,108],[103,101,110,94,93,111,95,109],[39,102,111,95,94,47,31,110],[105,112,96,113,97],[106,104,113,97,114,96,98,112],[107,105,114,98,115,97,99,113],[108,106,115,99,116,98,100,114],[109,107,116,100,117,99,101,115],[110,108,117,101,100,118,102,116],[111,109,118,102,101,119,103,117],[47,110,119,103,102,55,39,118],[113,120,104,121,105],[114,112,121,105,122,104,106,120],[115,113,122,106,123,105,107,121],[116,114,123,107,124,106,108,122],[117,115,124,108,125,107,109,123],[118,116,125,109,126,108,110,124],[119,117,126,110,109,127,111,125],[55,118,127,111,110,63,47,126],[121,56,112,57,113],[122,120,57,113,58,112,114,56],[123,121,58,114,59,113,115,57],[124,122,59,115,60,114,116,58],[125,123,60,116,61,115,117,59],[126,124,61,117,62,116,118,60],[127,125,62,118,63,117,119,61],[63,126,119,118,55,62]];

whitePawnLines = [[0,1,2,3,4,5,6,7],[8,9,10,11,12,13,14,15],[16,17,18,19,20,21,22,23],[24,25,26,27,28,29,30,31],[32,33,34,35,36,37,38,39],[40,41,42,43,44,45,46,47],[48,49,50,51,52,53,54,55],[56,57,58,59,60,61,62,63],[64,65,66,67,68,69,70,71],[72,73,74,75,76,77,78,79],[80,81,82,83,84,85,86,87],[88,89,90,91,92,93,94,95],[96,97,98,99,100,101,102,103],[104,105,106,107,108,109,110,111],[112,113,114,115,116,117,118,119],[120,121,122,123,124,125,126,127]];

blackPawnLines = [[0,8,16,24,32,40,48,56],[1,9,17,25,33,41,49,57],[2,10,18,26,34,42,50,58],[3,11,19,27,35,43,51,59],[4,12,20,28,36,44,52,60],[5,13,21,29,37,45,53,61],[6,14,22,30,38,46,54,62],[7,15,23,31,39,47,55,63],[64,72,80,88,96,104,112,120],[65,73,81,89,97,105,113,121],[66,74,82,90,98,106,114,122],[67,75,83,91,99,107,115,123],[68,76,84,92,100,108,116,124],[69,77,85,93,101,109,117,125],[70,78,86,94,102,110,118,126],[71,79,87,95,103,111,119,127]];

whitePawnCaptures = [
[],[],[],[],[13],[14],[15],[],
[],[],[],[],[5,21],[6,22],[7,23],[],
[],[],[],[],[13,29],[14,30],[15,31],[],
[],[],[],[],[21,37],[22,38],[23,39],[],
[41],[42],[43],[28,44],[29,45],[30,46],[31,47],[],
[33,49],[34,50],[35,51],[36,52],[37,53],[38,54],[39,55],[],
[41,57],[42,58],[43,59],[44,60],[45,61],[46,62],[47,63],[],
[49,121],[50,122],[51,123],[52,124],[53,125],[54,126],[55,127],[],
[],[],[],[],[77],[78],[79],[],
[],[],[],[],[69,85],[70,86],[71,87],[],
[],[],[],[],[77,93],[78,94],[79,95],[],
[],[],[],[],[85,101],[86,102],[87,103],[],
[105],[106],[107],[92,108],[93,109],[94,110],[95,111],[],
[97,113],[98,114],[99,115],[100,116],[101,117],[102,118],[103,119],[],
[105,121],[106,122],[107,123],[108,124],[109,125],[110,126],[111,127],[],
[113,57],[114,58],[115,59],[116,60],[117,61],[118,62],[119,63],[],
];

blackPawnCaptures = [
[],[],[],[],[13],[12,14],[13,15],[14,79],
[],[],[],[],[21],[20,22],[21,23],[22,87],
[],[],[],[],[29],[28,30],[29,31],[30,95],
[],[],[],[],[35,37],[36,38],[37,39],[38,103],
[41],[40,42],[41,43],[42,44],[43,45],[44,46],[45,47],[46,111],
[49],[48,50],[49,51],[50,52],[51,53],[52,54],[53,55],[54,119],
[57],[56,58],[57,59],[58,60],[59,61],[60,62],[61,63],[62,127],
[],[],[],[],[],[],[],[],
[],[],[],[],[77],[76,78],[77,79],[78,15],
[],[],[],[],[85],[84,86],[85,87],[86,23],
[],[],[],[],[93],[92,94],[93,95],[94,31],
[],[],[],[],[99,101],[100,102],[101,103],[102,39],
[105],[104,106],[105,107],[106,108],[107,109],[108,110],[109,111],[110,47],
[113],[112,114],[113,115],[114,116],[115,117],[116,118],[117,119],[118,55],
[121],[120,122],[121,123],[122,124],[123,125],[124,126],[125,127],[126,63],
[],[],[],[],[],[],[],[]];

castleSquares = [[104,112],[48,56],[69,70],[6,7]];

whiteBackRank = [32,40,48,56,120,112,104,96];
blackBackRank = [4,5,6,7,71,70,69,68];

class Piece {
  static all = [];

  static wk = -1;
  static bk = -1;

  static wrs = [-1,-1];
  static brs = [-1,-1];

  constructor(color,type,square) {
    if (Piece.at(square))
      throw `cannot create a piece on an occupied square`;
    this.color = color;
    this.type = type;
    this.square = square;
    if (type === 'king') {
      if (color === 'white') Piece.wk = square;
      if (color === 'black') Piece.bk = square;
    }
    this.move0 = true;
    Piece.all.push(this);
  }

  static clear() {
    Piece.all.length = 0;
    Piece.wrs.length = 0;
    Piece.brs.length = 0;
    Piece.wrs.push(-1,-1);
    Piece.brs.push(-1,-1);
    Piece.wk = -1;
    Piece.bk = -1;
  }

  static create(color,type,square) {
    switch (type) {
      case 'pawn': return new Pawn(color,square);
      case 'knight': return new Knight(color,square);
      case 'bishop': return new Bishop(color,square);
      case 'rook': return new Rook(color,square);
      case 'queen': return new Queen(color,square);
      case 'king': return new King(color,square);
    }
  }

  static at(square) {
    return Piece.all.find(piece => piece.square === square);
  }

  delete() {
    var all = Piece.all;
    var index = all.indexOf(this);
    if (index > -1) all.splice(index,1);
  }

  getMoves() {
    return [];
  }

}

class Pawn extends Piece {
  constructor(color,square) {
    super(color,'pawn',square);
    if (color === 'white') this.img = images.wp;
    else if (color === 'black') this.img = images.bp;
  }

  getMoves() {
    var moves = [], sq = this.square, color = this.color;
    var lines  = color==='white' ? whitePawnLines    : blackPawnLines;
    var caps   = color==='white' ? whitePawnCaptures : blackPawnCaptures;
    var promos = color==='white' ? whitePromoSet     : blackPromoSet;

    var line, idx = -1;
    for (var l of lines) { var i = l.indexOf(sq); if (i !== -1) { line=l; idx=i; break; } }
    if (!line || idx <= 0) return [];

    if (idx+1 < line.length) {
      var to = line[idx+1];
      if (!excl(to) && !Piece.at(to) && isLegal(this, to)) {
        if (promos.has(to)) {
          for (var pt of ['queen','rook','bishop','knight'])
            moves.push({from:sq, to, type:'promo', promo:pt});
        } else {
          moves.push({from:sq, to, type:'normal'});
          if (idx===1 && idx+2 < line.length) {
            var to2 = line[idx+2];
            if (!excl(to2) && !Piece.at(to2) && isLegal(this, to2))
              moves.push({from:sq, to:to2, type:'double', epSq:line[idx+1]});
          }
        }
      }
    }

    for (var to of (caps[sq]||[])) {
      if (excl(to)) continue;
      var target = Piece.at(to);
      if (target && target.color !== color && isLegal(this, to))
        if (promos.has(to)) {
          for (var pt of ['queen','rook','bishop','knight'])
            moves.push({from:sq, to, type:'promo', promo:pt});
        } else {
          moves.push({from:sq, to, type:'capture'});
        }
      if (to === gameState.epSquare) {
        var epP = Piece.at(gameState.epPawn);
        if (epP && epP.color !== color && isLegal(this, to, gameState.epPawn)) {
          if (promos.has(to)) {
            for (var pt of ['queen','rook','bishop','knight'])
              moves.push({from:sq, to, type:'enpassant_promo', promo:pt, epPawn:gameState.epPawn});
          } else {
            moves.push({from:sq, to, type:'enpassant', epPawn:gameState.epPawn});
          }
        }
      }
    }
    return moves;
  }
}

class Knight extends Piece {
  constructor(color,square) {
    super(color,'knight',square);
    if (color === 'white') this.img = images.wn;
    else if (color === 'black') this.img = images.bn;
  }

  getMoves() {
    var sq=this.square, c=this.color;
    return jumpSqs(sq, c, knightOffsets)
      .filter(to => isLegal(this, to))
      .map(to => ({from:sq, to, type:'normal'}));
  }
}

class Bishop extends Piece {
  constructor(color,square) {
    super(color,'bishop',square);
    if (color === 'white') this.img = images.wb;
    else if (color === 'black') this.img = images.bb;
  }

  getMoves() {
    var sq=this.square, c=this.color;
    return slideMoves(sq, c, bishopLines)
      .filter(to => isLegal(this, to))
      .map(to => ({from:sq, to, type:'normal'}));
  }
}

class Rook extends Piece {
  constructor(color,square) {
    super(color,'rook',square);
    if (color === 'white') this.img = images.wr;
    else if (color === 'black') this.img = images.br;
  }

  getMoves() {
    var sq=this.square, c=this.color;
    return slideMoves(sq, c, rookLines)
      .filter(to => isLegal(this, to))
      .map(to => ({from:sq, to, type:'normal'}));
  }
}

class Queen extends Piece {
  constructor(color,square) {
    super(color,'queen',square);
    if (color === 'white') this.img = images.wq;
    else if (color === 'black') this.img = images.bq;
  }

  getMoves() {
    var sq=this.square, c=this.color;
    return [...slideMoves(sq,c,rookLines), ...slideMoves(sq,c,bishopLines)]
      .filter(to => isLegal(this, to))
      .map(to => ({from:sq, to, type:'normal'}));
  }
}

class King extends Piece {
  constructor(color,square) {
    super(color,'king',square);
    if (color === 'white') this.img = images.wk;
    else if (color === 'black') this.img = images.bk;
  }

  getMoves() {
    var sq=this.square, color=this.color;
    var moves = jumpSqs(sq, color, kingOffsets)
      .filter(to => isLegal(this, to))
      .map(to => ({from:sq, to, type:'normal'}));

    if (!this.move0 || inCheck(color)) return moves;

    for (var [ks,rs,kd,rd,c] of CASTLE_DATA) {
      if (c !== color || ks !== sq) continue;
      var rook = Piece.at(rs);
      if (!rook || rook.type!=='rook' || rook.color!==color || !rook.move0) continue;

      var line = findLineWith(sq, rs);
      if (!line) continue;

      var ki=line.indexOf(sq), ri=line.indexOf(rs), kdi=line.indexOf(kd);

      var lo=Math.min(ki,ri), hi=Math.max(ki,ri), clear=true;
      for (var j=lo+1; j<hi; j++) {
        if (Piece.at(line[j]) || excl(line[j])) { clear=false; break; }
      }
      if (!clear) continue;

      var step=kdi>ki?1:-1, safe=true;
      for (var j=ki+step; j!==kdi+step; j+=step) {
        var tsq = line[j];
        this.square = tsq;
        if (color==='white') Piece.wk=tsq; else Piece.bk=tsq;
        var hit = isAttacked(tsq, opp(color));
        this.square = sq;
        if (color==='white') Piece.wk=sq; else Piece.bk=sq;
        if (hit) { safe=false; break; }
      }
      if (!safe) continue;

      moves.push({from:sq, to:kd, type:'castle', rookFrom:rs, rookTo:rd});
    }
    return moves;
  }
}

function newGame() {
  Piece.clear();
  Piece.create('white','pawn',33);
  Piece.create('white','pawn',41);
  Piece.create('white','pawn',49);
  Piece.create('white','pawn',57);
  Piece.create('white','pawn',97);
  Piece.create('white','pawn',105);
  Piece.create('white','pawn',113);
  Piece.create('white','pawn',121);
  Piece.create('white','rook',32);
  Piece.create('white','knight',40);
  Piece.create('white','bishop',48);
  Piece.create('white','queen',56);
  Piece.create('white','king',120);
  Piece.create('white','bishop',112);
  Piece.create('white','knight',104);
  Piece.create('white','rook',96);
  Piece.create('black','pawn',12);
  Piece.create('black','pawn',13);
  Piece.create('black','pawn',14);
  Piece.create('black','pawn',15);
  Piece.create('black','pawn',79);
  Piece.create('black','pawn',78);
  Piece.create('black','pawn',77);
  Piece.create('black','pawn',76);
  Piece.create('black','rook',4);
  Piece.create('black','knight',5);
  Piece.create('black','bishop',6);
  Piece.create('black','queen',7);
  Piece.create('black','king',71);
  Piece.create('black','bishop',70);
  Piece.create('black','knight',69);
  Piece.create('black','rook',68);
}

newGame();

mouse.grabbing = null;

var gameState = {
  turn:          'white',
  epSquare:      -1,
  epPawn:        -1,
  selectedMoves: [],
};

var selectedPiece = null;

var opp  = c => c === 'white' ? 'black' : 'white';
var excl = sq => excludedSquares.includes(sq);

var whitePromoSet = new Set(whitePawnLines.map(l => l[l.length-1]));
var blackPromoSet = new Set(blackPawnLines.map(l => l[l.length-1]));

function slideMoves(sq, color, lineGroups) {
  var out = [];
  for (var lines of lineGroups) {
    for (var line of lines) {
      var idx = line.indexOf(sq);
      if (idx === -1) continue;
      for (var i = idx+1; i < line.length; i++) {
        var t = line[i]; if (excl(t)) break;
        var p = Piece.at(t);
        if (p) { if (p.color !== color) out.push(t); break; }
        out.push(t);
      }
      for (var i = idx-1; i >= 0; i--) {
        var t = line[i]; if (excl(t)) break;
        var p = Piece.at(t);
        if (p) { if (p.color !== color) out.push(t); break; }
        out.push(t);
      }
    }
  }
  return out;
}

function jumpSqs(sq, color, table) {
  return (table[sq] || []).filter(t =>
    !excl(t) && (!Piece.at(t) || Piece.at(t).color !== color));
}

function isAttacked(sq, byColor) {
  for (var p of Piece.all) {
    if (p.color !== byColor) continue;
    switch (p.type) {
      case 'pawn': {
        var caps = byColor==='white' ? whitePawnCaptures : blackPawnCaptures;
        if ((caps[p.square]||[]).includes(sq)) return true;
        break;
      }
      case 'knight':
        if ((knightOffsets[p.square]||[]).includes(sq)) return true; break;
      case 'king':
        if ((kingOffsets[p.square]||[]).includes(sq)) return true; break;
      case 'bishop':
        if (slideMoves(p.square,byColor,bishopLines).includes(sq)) return true; break;
      case 'rook':
        if (slideMoves(p.square,byColor,rookLines).includes(sq)) return true; break;
      case 'queen':
        if (slideMoves(p.square,byColor,rookLines).includes(sq) ||
            slideMoves(p.square,byColor,bishopLines).includes(sq)) return true; break;
    }
  }
  return false;
}

function inCheck(color) {
  var ks = color==='white' ? Piece.wk : Piece.bk;
  return ks !== -1 && isAttacked(ks, opp(color));
}


function isLegal(mover, to, epRemoveSq) {
  var from  = mover.square;
  var snap  = Piece.all.slice();
  var oldWk = Piece.wk, oldBk = Piece.bk;

  if (epRemoveSq !== undefined && epRemoveSq !== -1) {
    var ep = Piece.at(epRemoveSq);
    if (ep) Piece.all.splice(Piece.all.indexOf(ep), 1);
  }
  var cap = Piece.at(to);
  if (cap) Piece.all.splice(Piece.all.indexOf(cap), 1);

  mover.square = to;
  if (mover.type==='king') { if (mover.color==='white') Piece.wk=to; else Piece.bk=to; }

  var ok = !inCheck(mover.color);

  Piece.all.length = 0; for (var p of snap) Piece.all.push(p);
  mover.square = from; Piece.wk = oldWk; Piece.bk = oldBk;
  return ok;
}

var CASTLE_DATA = [
  [120, 96,  castleSquares[0][0], castleSquares[0][1], 'white'],
  [120, 32,  castleSquares[1][0], castleSquares[1][1], 'white'],
  [71,  68,  castleSquares[2][0], castleSquares[2][1], 'black'],
  [71,  4,   castleSquares[3][0], castleSquares[3][1], 'black'],
];

function findLineWith(sq1, sq2) {
  for (var lines of rookLines)
    for (var line of lines)
      if (line.includes(sq1) && line.includes(sq2)) return line;
  return null;
}

function makeMove(move) {
  var piece = Piece.at(move.from);
  if (!piece) return;

  gameState.epSquare = -1;
  gameState.epPawn   = -1;

  switch (move.type) {
    case 'castle': {
      var rook = Piece.at(move.rookFrom);
      if (rook) { rook.square = move.rookTo; rook.move0 = false; }
      if (piece.color==='white') Piece.wk=move.to; else Piece.bk=move.to;
      piece.square = move.to; piece.move0 = false;
      break;
    }
    case 'enpassant': {
      var ep = Piece.at(move.epPawn); if (ep) ep.delete();
      piece.square = move.to; piece.move0 = false;
      break;
    }
    case 'promo': {
      var cap = Piece.at(move.to); if (cap) cap.delete();
      var col = piece.color; piece.delete();
      Piece.create(col, move.promo, move.to);
      break;
    }
    case 'enpassant_promo': {
      var ep = Piece.at(move.epPawn); if (ep) ep.delete();
      var col = piece.color; piece.delete();
      Piece.create(col, move.promo, move.to);
      break;
    }
    case 'double': {
      piece.square = move.to; piece.move0 = false;
      gameState.epSquare = move.epSq;
      gameState.epPawn   = move.to;
      break;
    }
    default: {
      var cap = Piece.at(move.to); if (cap) cap.delete();
      if (piece.type==='king') {
        if (piece.color==='white') Piece.wk=move.to; else Piece.bk=move.to;
      }
      piece.square = move.to; piece.move0 = false;
    }
  }

  gameState.turn = opp(gameState.turn);
  gameState.selectedMoves = [];
  selectedPiece = null;
}

mouse.leftFrom = null;
mouse.wasSelected = false;
mouse.selected = null;

function onMouseDown() {
  if (window.myColor && gameState.turn !== window.myColor) {
    mouse.selected = null; selectedPiece = null; gameState.selectedMoves = []; return;
  }
  if (mouse.selected !== null) {
    if (uimake(mouse.id)) return;
  }
  var piece = Piece.at(mouse.id);
  if (piece) {
    mouse.leftFrom = mouse.id;
    mouse.grabbing = piece;
    mouse.wasSelected = mouse.selected === mouse.id;
    mouse.selected = mouse.id;
    selectedPiece   = piece;
    if (piece.color === gameState.turn) {
      gameState.selectedMoves = piece.getMoves();
      return
    }
  }
    mouse.selected = null
    selectedPiece   = null;
    gameState.selectedMoves = [];

}

function onMouseUp() {
  if (!mouse.grabbing) return;
  var piece    = mouse.grabbing;
  var targetSq = mouse.id;
  mouse.grabbing = null;
  if (uimake(targetSq)) return;
  if (mouse.id === mouse.leftFrom && mouse.wasSelected) {
    selectedPiece = null;
    mouse.selected = null;
    gameState.selectedMoves = [];
  }
}


function uimake(targetSq) {
  if (!excl(targetSq) && targetSq !== undefined) {
    var move = gameState.selectedMoves.find(m => m.to === targetSq);
    if (move) {
      // auto-promote 4 now
      if (move.type === 'promo')
        move = gameState.selectedMoves.find(m => m.to===targetSq && m.promo==='queen') || move;
      if (window._netMove) {
        makeMove(move);
        window._netMove(move);
        gameState.selectedMoves = [];
        selectedPiece = null;
        mouse.selected = null;
      } else {
        makeMove(move);
      }
      return true;
    }
  }
}

function onMouseMove() {}

function applyServerState(s) {
  Piece.clear();
  for (var p of s.pieces) {
    var piece = Piece.create(p.color, p.type, p.square);
    piece.move0 = p.move0;
  }
  gameState.turn = s.turn;
  gameState.epSquare = s.epSquare;
  gameState.epPawn   = s.epPawn;
  gameState.selectedMoves = [];
  selectedPiece = null;
  mouse.selected = null;
  mouse.grabbing = null;
  // force redraw for turn indicator
  turnSync = null;
}
window.applyServerState = applyServerState;

var dots = bxx.concat(nxx).map(bx => {
  var f = bx.flat();
  var b0=f[0],b1=f[1], b4=f[4],b5=f[5], b8=f[8],b9=f[9], b12=f[12],b13=f[13];
  var cx = (b0 + b4 + b8 + b12) / 4;
  var cy = (b1 + b5 + b9 + b13) / 4;
  var w = (Math.abs(b8 - b0) + Math.abs(b4 - b12)) / 2;
  var h = (Math.abs(b5 - b1) + Math.abs(b9 - b13)) / 2;
  var r = Math.max(w, h) * 0.2;
  return [cx, cy, r];
});

function hl() {
  for (var move of gameState.selectedMoves) {
    var to = move.to;
    if (to < 0 || to >= dots.length || excl(to)) continue;
    var [cx, cy, r] = dots[to];
    var sc = s / 40;
    if (window.myColor === 'black') {
      cx = 40 - cx;
      cy = 40 - cy;
    }
    ctx.fillStyle = '#cba6f7';
    ctx.globalAlpha = .62;
    ctx.beginPath();
    ctx.arc(cx * sc, (40 - cy) * sc, r * sc, 0, Math.PI * 2);
    ctx.fill();
    ctx.closePath();
    ctx.globalAlpha = 1;
  }
}

// turn indication
var turnSync = null;
var overlay = document.createElement('div');
document.body.appendChild(overlay);
overlay.style.position = 'absolute';
overlay.style.left = '0px';
overlay.style.top = '0px';
overlay.style.width = '100%';
overlay.style.height = 'calc(100% - 10px)';
overlay.style.zIndex = '-1';
var psych = false;
var secret = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','KeyB','KeyA','Enter'];
window.onkeydown = function(event) {
  if (secret.shift() === event.code) {
    if (secret.length === 0) {
      psych = !psych;
    } else {
      return;
    }
  }
  secret = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','KeyB','KeyA','Enter'];
}

function draw() {
var X = performance.now()/100%360;
// only update if state has changed
if (gameState.turn !== turnSync) {
  turnSync = gameState.turn;
  // if turn = user color, draw on bottom
  if (turnSync === (window.myColor ?? 'white')) {
    overlay.style.borderTop = 'none';
    overlay.style.borderBottom = '8px solid #a6e3a1';
  // else, draw on top
  } else {
    overlay.style.borderTop = '8px solid #6c7086';
    overlay.style.borderBottom = 'none';
  }
}

var flipped = window.myColor === 'black';
ctx.clearRect(0,0,s,s);

db.forEach((fn,i) => {
  var x = i & 7;
  var y = i >> 3;
  if ( x < 4 && y < 4 ) return;
  var p = (x + y + flipped) % 2;
  if (psych) {
    ctx.fillStyle = 'hsl('+(i*X%360)+', 100%, 50%)';
  } else {
    ctx.fillStyle = p ? '#45475a' : '#313244';
  }
  ctx.beginPath();
  fn();
  ctx.fill();
  ctx.closePath();
})

nb.forEach((fn,i) => {
  var x = i & 7;
  var y = i >> 3;
  if ( x < 4 && y < 4 ) return;
  var p = (x + y + flipped) % 2;
  if (psych) {
    ctx.fillStyle = 'hsl('+(i*X%360)+', 100%, 50%)';
  } else {
    ctx.fillStyle = p ? '#313244' : '#45475a';
  }
  ctx.beginPath();
  fn();
  ctx.fill();
  ctx.closePath();
})

hl();

ctx.beginPath();
ctx.strokeStyle = '#181825';
ctx.lineWidth = Math.max(1, s / 520);
moveTo(4,8);
bezTo(20,40,36,8);
drawBez(8,6.25,20,38.25,32,6.25);
drawBez(12,5,20,37,28,5);
drawBez(16,4.25,20,36.25,24,4.25);
drawBez(10,22.25,20,30.25,30,22.25);
drawBez(8,25,20,33,32,25);
drawBez(6,28.25,20,36.25,34,28.25);
drawBez(4,32,20,40,36,32);
drawBez(4,32,20,0,36,32);
drawBez(8,33.75,20,1.75,32,33.75);
drawBez(12,35,20,3,28,35);
drawBez(16,35.75,20,3.75,24,35.75);
drawBez(10,17.75,20,9.75,30,17.75);
drawBez(8,15,20,7,32,15);
drawBez(6,11.75,20,3.75,34,11.75);
drawBez(4,8,20,0,36,8);
drawLine(20,4,20,36);
ctx.stroke();
ctx.closePath();

Piece.all.forEach(piece => {
if (mouse.grabbing === piece) return;
  var sq = piece.square;
  var sig = 8 - (sq >> 3 & 7);
  var rho = 8 - (sq & 7);
  if (flipped) {
      drawImage(piece.img,rho-.5,-sig+.5,sq < 64,piece.color === 'white');
  } else {
      drawImage(piece.img,sig-.5,rho-.5,sq < 64,piece.color === 'black');
  }
});

if (mouse.grabbing) {
  var piece = mouse.grabbing;
  var sq = mouse.id;
  var sig = mouse.sig;
  var rho = mouse.rho;
  if (flipped) {
      drawImage(piece.img,rho,-sig,sq < 64,piece.color === 'white');
  } else {
      drawImage(piece.img,sig,rho,sq < 64,piece.color === 'black');
  }
}
}

function loop() {
  requestAnimationFrame(loop);
  draw();
}

loop();
