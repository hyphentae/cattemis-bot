'use strict';

function createGame() {

  var excludedSquares = [
    0,1,2,3,8,9,10,11,16,17,18,19,24,25,26,27,
    64,65,66,67,72,73,74,75,80,81,82,83,88,89,90,91,
  ];

  var rookLines = [[
    [4,5,6,7,71,70,69,68],
    [12,13,14,15,79,78,77,76],
    [20,21,22,23,87,86,85,84],
    [28,29,30,31,95,94,93,92],
    [32,33,34,35,36,37,38,39,103,102,101,100,99,98,97,96],
    [40,41,42,43,44,45,46,47,111,110,109,108,107,106,105,104],
    [48,49,50,51,52,53,54,55,119,118,117,116,115,114,113,112],
    [56,57,58,59,60,61,62,63,127,126,125,124,123,122,121,120],
  ],[
    [32,40,48,56,120,112,104,96],
    [33,41,49,57,121,113,105,97],
    [34,42,50,58,122,114,106,98],
    [35,43,51,59,123,115,107,99],
    [4,12,20,28,36,44,52,60,124,116,108,100,92,84,76,68],
    [5,13,21,29,37,45,53,61,125,117,109,101,93,85,77,69],
    [6,14,22,30,38,46,54,62,126,118,110,102,94,86,78,70],
    [7,15,23,31,39,47,55,63,127,119,111,103,95,87,79,71],
  ]];

  var bishopLines = [[
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

  var knightOffsets = [[],[],[],[],[14,21],[15,20,22],[12,79,21,23],[13,78,22,87],[],[],[],[],[6,22,29],[7,23,28,30],[4,20,87,71,29,31],[5,21,86,70,30,95],[],[],[],[],[14,30,5,35,37],[15,31,4,6,36,38],[12,28,95,79,5,7,37,39],[13,29,94,78,6,71,38,103],[],[],[],[],[22,38,13,43,45],[23,39,12,14,44,46],[20,36,103,87,13,15,45,47],[21,37,102,86,14,79,46,111],[42,49],[43,48,50],[40,28,44,49,51],[41,29,45,50,52],[42,30,46,21,51,53],[43,31,47,20,22,52,54],[28,44,111,95,21,23,53,55],[29,45,110,94,22,87,54,119],[34,50,57],[35,51,56,58],[32,48,36,52,57,59],[33,49,37,53,58,60],[34,50,38,54,29,59,61],[35,51,39,55,28,30,60,62],[36,52,119,103,29,31,61,63],[37,53,118,102,30,95,62,127],[42,58,33,121],[43,59,32,34,122,120],[40,56,44,60,33,35,123,121],[41,57,45,61,34,36,124,122],[42,58,46,62,35,37,125,123],[43,59,47,63,36,38,126,124],[44,60,127,111,37,39,127,125],[45,61,126,110,38,103,63,126],[50,122,41,113],[51,123,40,42,114,112],[48,120,52,124,41,43,115,113],[49,121,53,125,42,44,116,114],[50,122,54,126,43,45,117,115],[51,123,55,127,44,46,118,116],[52,124,63,119,45,47,119,117],[53,125,62,118,46,111,55,118],[],[],[],[],[78,85],[79,86,84],[15,76,87,85],[14,77,23,86],[],[],[],[],[86,70,93],[87,71,94,92],[7,23,84,68,95,93],[6,22,85,69,31,94],[],[],[],[],[94,78,101,99,69],[95,79,102,100,70,68],[15,31,92,76,103,101,71,69],[14,30,93,77,39,102,7,70],[],[],[],[],[102,86,109,107,77],[103,87,110,108,78,76],[23,39,100,84,111,109,79,77],[22,38,101,85,47,110,15,78],[106,113],[107,114,112],[108,92,104,115,113],[109,93,105,116,114],[110,94,106,117,115,85],[111,95,107,118,116,86,84],[31,47,108,92,119,117,87,85],[30,46,109,93,55,118,23,86],[114,98,121],[115,99,122,120],[116,100,112,96,123,121],[117,101,113,97,124,122],[118,102,114,98,125,123,93],[119,103,115,99,126,124,94,92],[39,55,116,100,127,125,95,93],[38,54,117,101,63,126,31,94],[122,106,57,97],[123,107,56,58,98,96],[124,108,120,104,57,59,99,97],[125,109,121,105,58,60,100,98],[126,110,122,106,59,61,101,99],[127,111,123,107,60,62,102,100],[47,63,124,108,61,63,103,101],[46,62,125,109,62,127,39,102],[58,114,49,105],[59,115,48,50,106,104],[60,116,56,112,49,51,107,105],[61,117,57,113,50,52,108,106],[62,118,58,114,51,53,109,107],[63,119,59,115,52,54,110,108],[55,127,60,116,53,55,111,109],[54,126,61,117,54,119,47,110]];

  var kingOffsets = [[],[],[],[],[5,12,13],[4,6,13,12,14],[5,7,14,13,15],[6,71,15,14,79],[],[],[],[],[13,4,20,5,21],[12,14,5,21,6,20,4,22],[13,15,6,22,7,21,5,23],[14,79,7,23,71,22,6,87],[],[],[],[],[21,12,28,13,29],[20,22,13,29,14,28,12,30],[21,23,14,30,15,29,13,31],[22,87,15,31,79,30,14,95],[],[],[],[],[29,20,36,21,35,37],[28,30,21,37,22,36,20,38],[29,31,22,38,23,37,21,39],[30,95,23,39,87,38,22,103],[33,40,41],[32,34,41,40,42],[33,35,42,41,43],[34,36,43,28,42,44],[35,37,28,44,29,43,45],[36,38,29,45,30,44,46,28],[37,39,30,46,31,45,29,47],[38,103,31,47,95,46,30,111],[41,32,48,33,49],[40,42,33,49,34,48,50,32],[41,43,34,50,35,49,51,33],[42,44,35,51,36,50,52,34],[43,45,36,52,37,51,53,35],[44,46,37,53,38,52,36,54],[45,47,38,54,39,53,55,37],[46,111,39,55,103,54,38,119],[49,40,56,41,57],[48,50,41,57,42,56,58,40],[49,51,42,58,43,57,59,41],[50,52,43,59,44,58,60,42],[51,53,44,60,45,59,61,43],[52,54,45,61,46,60,62,44],[53,55,46,62,47,61,45,63],[54,119,47,63,111,62,127,46],[57,48,120,49,121],[56,58,49,121,50,120,122,48],[57,59,50,122,51,121,123,49],[58,60,51,123,52,122,124,50],[59,61,52,124,53,123,125,51],[60,62,53,125,54,124,126,52],[61,63,54,126,55,125,127,53],[62,127,55,119,126,54],[],[],[],[],[69,76,77],[70,68,77,78,76],[71,69,78,79,77],[7,70,79,15,78],[],[],[],[],[77,84,68,85,69],[78,76,85,69,68,86,70,84],[79,77,86,70,69,87,71,85],[15,78,87,71,70,23,7,86],[],[],[],[],[85,92,76,93,77],[86,84,93,77,76,94,78,92],[87,85,94,78,77,95,79,93],[23,86,95,79,78,31,15,94],[],[],[],[],[93,100,84,101,85,99],[94,92,101,85,84,102,86,100],[95,93,102,86,85,103,87,101],[31,94,103,87,86,39,23,102],[97,104,105],[98,96,105,106,104],[99,97,106,107,105],[100,98,107,108,92,106],[101,99,108,92,109,93,107],[102,100,109,93,92,110,94,108],[103,101,110,94,93,111,95,109],[39,102,111,95,94,47,31,110],[105,112,96,113,97],[106,104,113,97,114,96,98,112],[107,105,114,98,115,97,99,113],[108,106,115,99,116,98,100,114],[109,107,116,100,117,99,101,115],[110,108,117,101,100,118,102,116],[111,109,118,102,101,119,103,117],[47,110,119,103,102,55,39,118],[113,120,104,121,105],[114,112,121,105,122,104,106,120],[115,113,122,106,123,105,107,121],[116,114,123,107,124,106,108,122],[117,115,124,108,125,107,109,123],[118,116,125,109,126,108,110,124],[119,117,126,110,109,127,111,125],[55,118,127,111,110,63,47,126],[121,56,112,57,113],[122,120,57,113,58,112,114,56],[123,121,58,114,59,113,115,57],[124,122,59,115,60,114,116,58],[125,123,60,116,61,115,117,59],[126,124,61,117,62,116,118,60],[127,125,62,118,63,117,119,61],[63,126,119,118,55,62]];

  var whitePawnLines = [[0,1,2,3,4,5,6,7],[8,9,10,11,12,13,14,15],[16,17,18,19,20,21,22,23],[24,25,26,27,28,29,30,31],[32,33,34,35,36,37,38,39],[40,41,42,43,44,45,46,47],[48,49,50,51,52,53,54,55],[56,57,58,59,60,61,62,63],[64,65,66,67,68,69,70,71],[72,73,74,75,76,77,78,79],[80,81,82,83,84,85,86,87],[88,89,90,91,92,93,94,95],[96,97,98,99,100,101,102,103],[104,105,106,107,108,109,110,111],[112,113,114,115,116,117,118,119],[120,121,122,123,124,125,126,127]];

  var blackPawnLines = [[0,8,16,24,32,40,48,56],[1,9,17,25,33,41,49,57],[2,10,18,26,34,42,50,58],[3,11,19,27,35,43,51,59],[4,12,20,28,36,44,52,60],[5,13,21,29,37,45,53,61],[6,14,22,30,38,46,54,62],[7,15,23,31,39,47,55,63],[64,72,80,88,96,104,112,120],[65,73,81,89,97,105,113,121],[66,74,82,90,98,106,114,122],[67,75,83,91,99,107,115,123],[68,76,84,92,100,108,116,124],[69,77,85,93,101,109,117,125],[70,78,86,94,102,110,118,126],[71,79,87,95,103,111,119,127]];

  var whitePawnCaptures = [
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

  var blackPawnCaptures = [
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
    [],[],[],[],[],[],[],[]
  ];

  var castleSquares = [[104,112],[48,56],[69,70],[6,7]];

  var allPieces = [];
  var wk = -1, bk = -1;
  var gs = { turn: 'white', epSquare: -1, epPawn: -1 };

  var opp  = c => c === 'white' ? 'black' : 'white';
  var excl = sq => excludedSquares.includes(sq);
  var whitePromoSet = new Set(whitePawnLines.map(l => l[l.length - 1]));
  var blackPromoSet = new Set(blackPawnLines.map(l => l[l.length - 1]));

  class Piece {
    constructor(color, type, square) {
      this.color  = color;
      this.type   = type;
      this.square = square;
      this.move0  = true;
      if (type === 'king') { if (color === 'white') wk = square; else bk = square; }
      allPieces.push(this);
    }
    static at(sq) { return allPieces.find(p => p.square === sq); }
    delete() { var i = allPieces.indexOf(this); if (i > -1) allPieces.splice(i, 1); }
    getMoves() { return []; }
    static clear() { allPieces.length = 0; wk = -1; bk = -1; }
    static create(color, type, square) {
      switch (type) {
        case 'pawn':   return new Pawn(color, square);
        case 'knight': return new Knight(color, square);
        case 'bishop': return new Bishop(color, square);
        case 'rook':   return new Rook(color, square);
        case 'queen':  return new Queen(color, square);
        case 'king':   return new King(color, square);
      }
    }
  }

  class Pawn extends Piece {
    constructor(color, square) { super(color, 'pawn', square); }
    getMoves() {
      var moves = [], sq = this.square, color = this.color;
      var lines  = color === 'white' ? whitePawnLines    : blackPawnLines;
      var caps   = color === 'white' ? whitePawnCaptures : blackPawnCaptures;
      var promos = color === 'white' ? whitePromoSet     : blackPromoSet;
      var line, idx = -1;
      for (var l of lines) { var i = l.indexOf(sq); if (i !== -1) { line = l; idx = i; break; } }
      if (!line || idx <= 0) return [];
      if (idx + 1 < line.length) {
        var to = line[idx + 1];
        if (!excl(to) && !Piece.at(to) && isLegal(this, to)) {
          if (promos.has(to)) {
            for (var pt of ['queen','rook','bishop','knight'])
              moves.push({ from: sq, to, type: 'promo', promo: pt });
          } else {
            moves.push({ from: sq, to, type: 'normal' });
            if (idx === 1 && idx + 2 < line.length) {
              var to2 = line[idx + 2];
              if (!excl(to2) && !Piece.at(to2) && isLegal(this, to2))
                moves.push({ from: sq, to: to2, type: 'double', epSq: line[idx + 1] });
            }
          }
        }
      }
      for (var to of (caps[sq] || [])) {
        if (excl(to)) continue;
        var target = Piece.at(to);
        if (target && target.color !== color && isLegal(this, to))
          if (promos.has(to)) {
            for (var pt of ['queen','rook','bishop','knight'])
              moves.push({ from: sq, to, type: 'promo', promo: pt });
          } else {
            moves.push({ from: sq, to, type: 'capture' });
          }
        if (to === gs.epSquare) {
          var epP = Piece.at(gs.epPawn);
          if (epP && epP.color !== color && isLegal(this, to, gs.epPawn)) {
            if (promos.has(to)) {
              for (var pt of ['queen','rook','bishop','knight'])
                moves.push({ from: sq, to, type: 'enpassant_promo', promo: pt, epPawn: gs.epPawn });
            } else {
              moves.push({ from: sq, to, type: 'enpassant', epPawn: gs.epPawn });
            }
          }
        }
      }
      return moves;
    }
  }

  class Knight extends Piece {
    constructor(color, square) { super(color, 'knight', square); }
    getMoves() {
      var sq = this.square, c = this.color;
      return jumpSqs(sq, c, knightOffsets).filter(to => isLegal(this, to)).map(to => ({ from: sq, to, type: 'normal' }));
    }
  }

  class Bishop extends Piece {
    constructor(color, square) { super(color, 'bishop', square); }
    getMoves() {
      var sq = this.square, c = this.color;
      return slideMoves(sq, c, bishopLines).filter(to => isLegal(this, to)).map(to => ({ from: sq, to, type: 'normal' }));
    }
  }

  class Rook extends Piece {
    constructor(color, square) { super(color, 'rook', square); }
    getMoves() {
      var sq = this.square, c = this.color;
      return slideMoves(sq, c, rookLines).filter(to => isLegal(this, to)).map(to => ({ from: sq, to, type: 'normal' }));
    }
  }

  class Queen extends Piece {
    constructor(color, square) { super(color, 'queen', square); }
    getMoves() {
      var sq = this.square, c = this.color;
      return [...slideMoves(sq, c, rookLines), ...slideMoves(sq, c, bishopLines)]
        .filter(to => isLegal(this, to)).map(to => ({ from: sq, to, type: 'normal' }));
    }
  }

  class King extends Piece {
    constructor(color, square) { super(color, 'king', square); }
    getMoves() {
      var sq = this.square, color = this.color;
      var moves = jumpSqs(sq, color, kingOffsets)
        .filter(to => isLegal(this, to))
        .map(to => ({ from: sq, to, type: 'normal' }));
      if (!this.move0 || inCheck(color)) return moves;
      for (var [ks, rs, kd, rd, c] of CASTLE_DATA) {
        if (c !== color || ks !== sq) continue;
        var rook = Piece.at(rs);
        if (!rook || rook.type !== 'rook' || rook.color !== color || !rook.move0) continue;
        var line = findLineWith(sq, rs); if (!line) continue;
        var ki = line.indexOf(sq), ri = line.indexOf(rs), kdi = line.indexOf(kd);
        var lo = Math.min(ki, ri), hi = Math.max(ki, ri), clear = true;
        for (var j = lo + 1; j < hi; j++) { if (Piece.at(line[j]) || excl(line[j])) { clear = false; break; } }
        if (!clear) continue;
        var step = kdi > ki ? 1 : -1, safe = true;
        for (var j = ki + step; j !== kdi + step; j += step) {
          var tsq = line[j];
          this.square = tsq; if (color === 'white') wk = tsq; else bk = tsq;
          var hit = isAttacked(tsq, opp(color));
          this.square = sq; if (color === 'white') wk = sq; else bk = sq;
          if (hit) { safe = false; break; }
        }
        if (!safe) continue;
        moves.push({ from: sq, to: kd, type: 'castle', rookFrom: rs, rookTo: rd });
      }
      return moves;
    }
  }

  function slideMoves(sq, color, lineGroups) {
    var out = [];
    for (var lines of lineGroups) {
      for (var line of lines) {
        var idx = line.indexOf(sq);
        if (idx === -1) continue;
        for (var i = idx + 1; i < line.length; i++) {
          var t = line[i]; if (excl(t)) break;
          var p = Piece.at(t);
          if (p) { if (p.color !== color) out.push(t); break; }
          out.push(t);
        }
        for (var i = idx - 1; i >= 0; i--) {
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
    return (table[sq] || []).filter(t => !excl(t) && (!Piece.at(t) || Piece.at(t).color !== color));
  }

  function isAttacked(sq, byColor) {
    for (var p of allPieces) {
      if (p.color !== byColor) continue;
      switch (p.type) {
        case 'pawn': {
          var caps = byColor === 'white' ? whitePawnCaptures : blackPawnCaptures;
          if ((caps[p.square] || []).includes(sq)) return true; break;
        }
        case 'knight': if ((knightOffsets[p.square] || []).includes(sq)) return true; break;
        case 'king':   if ((kingOffsets[p.square]   || []).includes(sq)) return true; break;
        case 'bishop': if (slideMoves(p.square, byColor, bishopLines).includes(sq)) return true; break;
        case 'rook':   if (slideMoves(p.square, byColor, rookLines).includes(sq))   return true; break;
        case 'queen':
          if (slideMoves(p.square, byColor, rookLines).includes(sq) ||
              slideMoves(p.square, byColor, bishopLines).includes(sq)) return true; break;
      }
    }
    return false;
  }

  function inCheck(color) {
    var ks = color === 'white' ? wk : bk;
    return ks !== -1 && isAttacked(ks, opp(color));
  }

  function isLegal(mover, to, epRemoveSq) {
    var from = mover.square, snap = allPieces.slice(), oldWk = wk, oldBk = bk;
    if (epRemoveSq !== undefined && epRemoveSq !== -1) {
      var ep = Piece.at(epRemoveSq); if (ep) allPieces.splice(allPieces.indexOf(ep), 1);
    }
    var cap = Piece.at(to); if (cap) allPieces.splice(allPieces.indexOf(cap), 1);
    mover.square = to;
    if (mover.type === 'king') { if (mover.color === 'white') wk = to; else bk = to; }
    var ok = !inCheck(mover.color);
    allPieces.length = 0; for (var p of snap) allPieces.push(p);
    mover.square = from; wk = oldWk; bk = oldBk;
    return ok;
  }

  function findLineWith(sq1, sq2) {
    for (var lines of rookLines)
      for (var line of lines)
        if (line.includes(sq1) && line.includes(sq2)) return line;
    return null;
  }

  var CASTLE_DATA = [
    [120, 96, castleSquares[0][0], castleSquares[0][1], 'white'],
    [120, 32, castleSquares[1][0], castleSquares[1][1], 'white'],
    [71,  68, castleSquares[2][0], castleSquares[2][1], 'black'],
    [71,   4, castleSquares[3][0], castleSquares[3][1], 'black'],
  ];

  function makeMove(move) {
    var piece = Piece.at(move.from); if (!piece) return;
    gs.epSquare = -1; gs.epPawn = -1;
    switch (move.type) {
      case 'castle': {
        var rook = Piece.at(move.rookFrom);
        if (rook) { rook.square = move.rookTo; rook.move0 = false; }
        if (piece.color === 'white') wk = move.to; else bk = move.to;
        piece.square = move.to; piece.move0 = false; break;
      }
      case 'enpassant': {
        var ep = Piece.at(move.epPawn); if (ep) ep.delete();
        piece.square = move.to; piece.move0 = false; break;
      }
      case 'promo': {
        var cap = Piece.at(move.to); if (cap) cap.delete();
        var col = piece.color; piece.delete();
        Piece.create(col, move.promo, move.to); break;
      }
      case 'enpassant_promo': {
        var ep = Piece.at(move.epPawn); if (ep) ep.delete();
        var col = piece.color; piece.delete();
        Piece.create(col, move.promo, move.to); break;
      }
      case 'double': {
        piece.square = move.to; piece.move0 = false;
        gs.epSquare = move.epSq; gs.epPawn = move.to; break;
      }
      default: {
        var cap = Piece.at(move.to); if (cap) cap.delete();
        if (piece.type === 'king') { if (piece.color === 'white') wk = move.to; else bk = move.to; }
        piece.square = move.to; piece.move0 = false;
      }
    }
    gs.turn = opp(gs.turn);
  }

  function newGame() {
    Piece.clear();
    for (var sq of [33,41,49,57,97,105,113,121]) Piece.create('white','pawn',sq);
    Piece.create('white','rook',32);  Piece.create('white','knight',40);
    Piece.create('white','bishop',48); Piece.create('white','queen',56);
    Piece.create('white','king',120);  Piece.create('white','bishop',112);
    Piece.create('white','knight',104); Piece.create('white','rook',96);
    for (var sq of [12,13,14,15,79,78,77,76]) Piece.create('black','pawn',sq);
    Piece.create('black','rook',4);   Piece.create('black','knight',5);
    Piece.create('black','bishop',6); Piece.create('black','queen',7);
    Piece.create('black','king',71);  Piece.create('black','bishop',70);
    Piece.create('black','knight',69); Piece.create('black','rook',68);
    gs.turn = 'white'; gs.epSquare = -1; gs.epPawn = -1;
  }

  newGame();

  function getState(extra) {
    return Object.assign({
      pieces:   allPieces.map(p => ({ color: p.color, type: p.type, square: p.square, move0: p.move0 })),
      turn:     gs.turn,
      epSquare: gs.epSquare,
      epPawn:   gs.epPawn,
      status:   null,
    }, extra || {});
  }

  function checkGameOver() {
    var color = gs.turn;
    for (var p of allPieces) if (p.color === color && p.getMoves().length > 0) return null;
    return inCheck(color) ? opp(color) + '_wins' : 'draw';
  }

  function applyMoveRequest(req) {
    if (gs.turn !== req.color) return false;
    var piece = Piece.at(req.from);
    if (!piece || piece.color !== req.color) return false;
    var moves = piece.getMoves();
    var move;
    if (req.promo) {
      move = moves.find(m => m.to === req.to && m.promo === req.promo);
    } else {
      // auto-queen promos
      move = moves.find(m => m.to === req.to && (m.promo === 'queen' || !m.promo));
    }
    if (!move) return false;
    makeMove(move);
    return true;
  }

  return { newGame, applyMoveRequest, getState, checkGameOver };
}

module.exports = { createGame };