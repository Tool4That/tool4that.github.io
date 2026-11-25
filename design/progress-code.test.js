// Tests for the Cyber progress code (design/progress-code.js). Run from the repository root:
//   node design/progress-code.test.js
// It runs prepare_tool.py --check-codec with the Python in PYTHON (default: py on Windows, python3 elsewhere), and it
// checks the codec against the kit's page-word check when ../tool4that-src-dlbackup/curriculum/build_study_map.py is
// there (or the file named in T4T_WORD_CHECK); without it, that one check is skipped and says so.
'use strict';
const fs = require('fs'), path = require('path'), os = require('os'), cp = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const FILE = path.join(__dirname, 'progress-code.js');
const C = require(FILE);
let fails = 0, passes = 0;
function check(ok, what, info) {
  if (ok) passes++; else fails++;
  console.log((ok ? 'PASS  ' : 'FAIL  ') + what + (info ? '  (' + info + ')' : ''));
}
const src = fs.readFileSync(FILE, 'utf8');
const part = name => { const m = src.match(new RegExp('/\\*@' + name + '\\*/([\\s\\S]*?)/\\*@/' + name + '\\*/')); return m ? m[1] : null; };
const ENC = part('encode'), DEC = part('decode');

// 1. One encoder source: CODE_ENC in prepare_tool.py equals the encode part, and the part runs on its own
{
  const py = process.env.PYTHON || (process.platform === 'win32' ? 'py' : 'python3');
  const r = cp.spawnSync(py, ['-I', 'prepare_tool.py', '--check-codec'], { cwd: ROOT, encoding: 'utf8', env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8' }) });
  check(r.status === 0, 'prepare_tool.py --check-codec: the encode part equals CODE_ENC byte for byte', ((r.stdout || '') + (r.stderr || '') + (r.error ? r.error.message : '')).trim());
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cy1-'));
  const one = path.join(dir, 'encode.js'), both = path.join(dir, 'both.js');
  fs.writeFileSync(one, ENC); fs.writeFileSync(both, ENC + DEC);
  const a = cp.spawnSync(process.execPath, ['--check', one], { encoding: 'utf8' });
  const b = cp.spawnSync(process.execPath, ['--check', both], { encoding: 'utf8' });
  check(a.status === 0, 'node --check passes on the encode part alone', a.stderr.trim());
  check(b.status === 0, 'node --check passes on the encode and decode parts together', b.stderr.trim());
  const vm = require('vm'), box = {};
  vm.runInNewContext(ENC + DEC + ';this.C=T4T_CODE;', box);
  check(typeof box.C.encode === 'function' && typeof box.C.read === 'function', 'the two parts alone define T4T_CODE with encode and read');
  check(!/\blet\b|\bconst\b|=>|`/.test(ENC + DEC), 'the codec is ES5: var only, no arrow functions or template strings');
  check(!/\beval\s*\(|new\s+Function/.test(ENC + DEC), 'the codec runs no code from strings');
  fs.rmSync(dir, { recursive: true, force: true });
}

// helpers
let seed = 20261124;
const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const norm = rec => JSON.stringify(Object.keys(rec).map(Number).sort((x, y) => x - y)
  .map(g => [g, String(rec[g]).replace(/0+$/, '')]).filter(x => x[1]));
const same = (a, b) => norm(a) === norm(b);
const states = (n, kind) => {
  let s = '';
  for (let i = 0; i < n; i++) {
    if (kind === 'one') s += '2';
    else if (kind === 'alt') s += i % 2 ? '1' : '2';
    else if (kind === 'runs') s += rnd() < 0.93 && s ? s.slice(-1) : String(Math.floor(rnd() * 3));
    else s += String(Math.floor(rnd() * 3));
  }
  return s;
};
function randomRecords() {
  const rec = {}, k = Math.floor(rnd() * 7);
  for (let j = 0; j < k; j++) {
    const g = 1 + Math.floor(rnd() * 63), n = 1 + Math.floor(rnd() * (rnd() < 0.05 ? 4095 : 400));
    rec[g] = states(n, ['one', 'alt', 'runs', 'mix'][Math.floor(rnd() * 4)]);
  }
  return rec;
}

// 2. Encode, then decode back
{
  const edge = [{}, { 1: '2' }, { 1: '1' }, { 63: '2' }, { 63: '1' }, { 1: '2'.repeat(4095) }, { 1: '1'.repeat(4095) },
    { 2: '0'.repeat(4094) + '2' }, { 5: states(4095, 'alt') }, { 1: '12', 63: '21' }, { 1: '000' }, { 7: '' },
    { 1: '2', 2: '1', 3: '2', 4: '1', 62: '2', 63: '1' }];
  let bad = 0, nondet = 0;
  const sets = edge.concat(Array.from({ length: 2000 }, randomRecords));
  for (const rec of sets) {
    const code = C.encode(rec), back = C.read(C.group(code));
    if (back.kind !== 'ok' || !same(back.records, rec)) bad++;
    if (C.encode(JSON.parse(JSON.stringify(rec))) !== code) nondet++;
  }
  check(bad === 0, 'encode then decode gives the same records for ' + sets.length + ' record sets (empty, one slot, g 63, n 4095, one state, alternating, random)', bad + ' differ');
  check(nondet === 0, 'the same records always give the same code', nondet + ' differ');
  check(C.encode({}) === 'CY1-Y' && C.read('CY1-Y').kind === 'ok' && norm(C.read('CY1-Y').records) === '[]', 'the empty code is CY1-Y and reads as empty');
  const g = C.group(C.encode({ 1: states(300, 'mix') }));
  check(/^CY1-[0-9A-Z]{5}( [0-9A-Z]{5})* ?[0-9A-Z]{0,5}$/.test(g) && !/ $/.test(g), 'group() shows the code in groups of five after CY1-', g.slice(0, 30) + '...');
}

// 3. Typo detection on 20 sample codes
const SEG = { 1: 662, 2: 84, 3: 92, 4: 71, 5: 53, 6: 47, 7: 140, 8: 117, 9: 146, 10: 182, 11: 60, 12: 67 };
function learner() {
  const rec = {};
  for (const g in SEG) {
    if (rnd() < 0.4) continue;
    const n = SEG[g], t = Math.floor(rnd() * n), pr = 0.5 + rnd() * 0.5, cl = rnd() < 0.5;
    let s = '';
    for (let i = 0; i < n; i++) s += (cl ? i < t : rnd() < t / n) ? (rnd() < pr ? '2' : '1') : '0';
    rec[g] = s;
  }
  return rec;
}
{
  const ok = x => C.read(x).kind === 'ok';
  let sub = 0, subOk = 0, sw = 0, swOk = 0, cut = 0, cutOk = 0, ins = 0, insOk = 0, del = 0, delOk = 0, two = 0, twoOk = 0;
  for (let k = 0; k < 20; k++) {
    const code = C.encode(learner());
    for (let i = 0; i < code.length; i++) {
      for (let j = 0; j < 32; j++) {
        const c = C.A[j];
        if (c !== code[i]) { sub++; if (ok(code.slice(0, i) + c + code.slice(i + 1))) subOk++; }
        if (i >= 4 && j % 8 === k % 8) { ins++; if (ok(code.slice(0, i) + c + code.slice(i))) insOk++; }
      }
      if (i + 1 < code.length && code[i] !== code[i + 1]) { sw++; if (ok(code.slice(0, i) + code[i + 1] + code[i] + code.slice(i + 2))) swOk++; }
      cut++; if (ok(code.slice(0, i))) cutOk++;
      if (i >= 4) { del++; if (ok(code.slice(0, i) + code.slice(i + 1))) delOk++; }
    }
    for (let r = 0; r < 500; r++) {
      const a = 4 + Math.floor(rnd() * (code.length - 4)), b = 4 + Math.floor(rnd() * (code.length - 4));
      if (a === b) continue;
      const x = code.split('');
      x[a] = C.A[(C.A.indexOf(x[a]) + 1 + Math.floor(rnd() * 31)) % 32];
      x[b] = C.A[(C.A.indexOf(x[b]) + 1 + Math.floor(rnd() * 31)) % 32];
      two++; if (ok(x.join(''))) twoOk++;
    }
  }
  check(subOk === 0, 'every single-character change of 20 sample codes is refused', sub + ' tried, ' + subOk + ' read');
  check(swOk === 0, 'every swap of two different neighboring characters is refused', sw + ' tried, ' + swOk + ' read');
  check(cutOk === 0, 'every truncation is refused', cut + ' tried, ' + cutOk + ' read');
  // the same in the grouped form people copy, where the reader also tries shorter runs that end at a group space
  let gsub = 0, gsubOk = 0, gsw = 0, gswOk = 0, gcut = 0, gcutOk = 0;
  for (let k = 0; k < 6; k++) {
    const code = C.encode(learner()), grp = C.group(code);
    for (let i = 0; i < grp.length; i++) {
      if (grp[i] === ' ' || grp[i] === '-') continue;
      for (let j = 0; j < 32; j++) { const c = C.A[j]; if (c !== grp[i] && !(i < 3)) { gsub++; if (ok(grp.slice(0, i) + c + grp.slice(i + 1))) gsubOk++; } }
      if (i >= 4 && i + 1 < grp.length && grp[i + 1] !== ' ' && grp[i] !== grp[i + 1]) { gsw++; if (ok(grp.slice(0, i) + grp[i + 1] + grp[i] + grp.slice(i + 2))) gswOk++; }
      if (i >= 5) { gcut++; if (ok(grp.slice(0, i))) gcutOk++; }
    }
  }
  check(gsubOk === 0 && gswOk === 0 && gcutOk === 0, 'in the grouped form too, every single-character change, neighbor swap, and truncation of 6 sample codes is refused',
    gsub + ' changes, ' + gsw + ' swaps, ' + gcut + ' truncations tried; ' + (gsubOk + gswOk + gcutOk) + ' read');
  const pct = (a, b) => (100 * a / b).toFixed(2) + '%';
  console.log('INFO  single insertions read as valid: ' + insOk + ' of ' + ins + ' (' + pct(insOk, ins) + '); single deletions: ' + delOk + ' of ' + del +
    ' (' + pct(delOk, del) + '); two random changes: ' + twoOk + ' of ' + two + ' (' + pct(twoOk, two) + ')');
}

// 4. Lenient reading, and the other kinds of text
{
  const rec = { 1: states(120, 'mix'), 9: states(40, 'runs') }, code = C.encode(rec), g = C.group(code);
  const reads = x => { const r = C.read(x); return r.kind === 'ok' && same(r.records, rec); };
  check(reads(code.toLowerCase()), 'lower case reads');
  check(reads(g) && reads('  ' + g.replace(/ /g, '\n') + '\n'), 'group spaces, other spaces, and line breaks read');
  check(reads(code.slice(0, 4) + code.slice(4).replace(/(.{3})/g, '$1-')), 'hyphens inside the payload read');
  check(reads(code.replace(/^CY1-/, 'CYl-')), 'an l typed for the 1 in CY1 reads');
  const samples = Array.from({ length: 400 }, randomRecords).map(r => C.encode(r));
  const withO = samples.find(c => /0/.test(c.slice(4))), withOne = samples.find(c => /1/.test(c.slice(4)));
  check(C.read(withO.slice(0, 4) + withO.slice(4).replace(/0/g, 'O')).kind === 'ok', 'O typed for 0 reads');
  check(C.read(withOne.slice(0, 4) + withOne.slice(4).replace(/1/g, 'I')).kind === 'ok' && C.read(withOne.slice(0, 4) + withOne.slice(4).replace(/1/g, 'L')).kind === 'ok', 'I and L typed for 1 read');
  check(reads('"' + g + '"') && reads('\u201c' + g + '\u201d') && reads('Code: ' + g + '.') && reads('My progress code is ' + g), 'a code inside quotes, after "Code:", or inside a sentence reads');
  check(reads(code.replace('CY1-', 'CY1\u2013')), 'a dash a word processor typed after CY1 reads');
  const u = code.slice(0, 6) + 'U' + code.slice(7);
  check(C.read(u).kind === 'damaged', 'U inside the code is damaged');
  check(C.read(code.slice(0, 6) + '*' + code.slice(7)).kind === 'damaged', 'another character inside the code ends it early, so the rest reads as damaged');
  check(C.read('CY2-ABCDE').kind === 'newer' && C.read('cy12-x').kind === 'newer', 'CY2- and later read as newer');
  check(C.read('CY0-ABCDE').kind === 'damaged', 'CY0- reads as damaged');
  check(C.read('DL1-f1q.f2m-1x9k2a').kind === 'dl' && C.read('Code: DL1-f1q-abc').kind === 'dl', 'a Defense Ladder code reads as one');
  check(C.read('DL1-a.se9cy1-1x9k2a').kind === 'dl', 'a Defense Ladder code whose ids hold "cy1-" still reads as a Defense Ladder code');
  check(C.read('hello there').kind === 'other' && C.read('').kind === 'other' && C.read(null).kind === 'other', 'other text reads as other');
  check(C.read('CY1-').kind === 'damaged' && C.read('CY1-  ').kind === 'damaged', 'CY1- alone is damaged');
  check(C.read(g + ' '.repeat(20001 - g.length)).kind === 'long' && C.read(g + ' '.repeat(19990 - g.length)).kind === 'ok', 'a paste over 20,000 characters is refused, one under it reads');
}

// 4b. The code inside a longer paste: words after it, invisible characters from chat apps, and quoted email lines
{
  const rec = { 1: '2212201', 7: '2'.repeat(30) + '1', 12: '0012' }, code = C.encode(rec), g = C.group(code);
  const reads = x => { const r = C.read(x); return r.kind === 'ok' && same(r.records, rec); };
  const pastes = [
    ['a sign-off on the next line', g + '\nMahalo, Kai'],
    ['words after it on the same line', g + ' from Kai'],
    ['a word made of code letters after it', g + ' OK'],
    ['a sentence around it that ends in a full stop', 'Here is my code: ' + g + '. Thanks!'],
    ['a label in brackets after it', g + ' (Freshman)'],
    ['Windows line breaks for the group spaces', g.replace(/ /g, '\r\n')],
    ['no-break spaces for the group spaces', g.replace(/ /g, ' ')],
    ['ideographic spaces for the group spaces', g.replace(/ /g, '　')],
    ['zero-width spaces (U+200B) for the group spaces', g.replace(/ /g, '​')],
    ['soft hyphens (U+00AD) for the group spaces', g.replace(/ /g, '­')],
    ['zero-width joiners and non-joiners (U+200C, U+200D) inside it', g.replace(/ /g, '‌').replace(/(.{9})/, '$1‍')],
    ['word joiners (U+2060) and a byte order mark (U+FEFF) inside it', '﻿' + g.replace(/ /g, '⁠')],
    ['a list bullet before it', '- ' + g],
    ['quoted email lines ("> ")', '> ' + g.replace(/ /g, '\n> ')],
    ['twice-quoted email lines (">> " and "> > ")', '>> ' + g.replace(/ /g, '\n> > ')],
    ['two codes in one paste (the first one reads)', g + '\n' + C.group(C.encode({ 2: '2' }))],
    ['lower case without spaces, then a word', code.toLowerCase() + ' thanks'],
  ];
  for (const [what, text] of pastes) check(reads(text), 'reads with ' + what);
  check(C.read('CY1-Y\nthanks').kind === 'ok' && norm(C.read('CY1-Y\nthanks').records) === '[]', 'the empty code CY1-Y reads with a word on the next line');
  check(C.read('cy1-y').kind === 'ok', 'the empty code typed in lower case reads');
  const typo = code.slice(0, 9) + C.A[(C.A.indexOf(code[9]) + 7) % 32] + code.slice(10);
  check(C.read(C.group(typo) + ' from Kai').kind === 'damaged' && C.read(C.group(typo) + '\nMahalo').kind === 'damaged', 'a code with a typo, followed by words, still reads as damaged');
  check(C.read(C.group(code).slice(0, -3) + ' thanks').kind === 'damaged', 'a code cut short, followed by a word, still reads as damaged');
  // a shorter run never stops between two groups of the code, so a typo can't make the start of a code read alone
  const full = Array.from({ length: 200 }, randomRecords).map(r => C.encode(r)).find(c => c.length > 20 && (c.length - 4) % 5 === 0), fg = C.group(full), fr = C.read(full).records;
  const readsFull = x => { const r = C.read(x); return r.kind === 'ok' && same(r.records, fr); };
  check(readsFull(fg + ' OK') && readsFull(fg + ' thx') && readsFull(fg + ' thanks') && readsFull(fg + '\nMahalo'),
    'a code whose last group has five characters reads with OK, a lower-case word, or a longer word after it');
  check(readsFull(fg + '\nKate') && readsFull(fg + ' Ty') && readsFull(fg + '\n- Sam') && readsFull(fg + '\nMana'),
    'it reads with a name in both letter cases after it (Kate, Ty, Sam, Mana), which never counts as a group');
  check(C.read(fg + ' THX').kind === 'damaged' && C.read(fg + ' 42').kind === 'damaged',
    'it reads as damaged with a short upper-case word of code characters or a number after it, which looks like one more group (copy the code alone)');
  // a typo typed in lower case makes its group mixed-case; the stop rule still never lets a shorter code read
  let lsub = 0, lsubOk = 0;
  for (let k = 0; k < 4; k++) {
    const lg = C.group(C.encode(learner()));
    for (let i = 4; i < lg.length; i++) {
      if (lg[i] === ' ') continue;
      for (const c of C.A) if (c !== lg[i] && /[A-Z]/.test(c)) { lsub++; if (C.read(lg.slice(0, i) + c.toLowerCase() + lg.slice(i + 1) + ' Ty').kind === 'ok') lsubOk++; }
    }
  }
  check(lsubOk === 0, 'a typo typed in lower case inside a grouped code, then a name, is refused', lsub + ' tried, ' + lsubOk + ' read');
  // the retry costs one pass over the paste: 20,000 characters of short words after CY1- read in well under a second
  const t0 = Date.now(), junk = C.read('CY1-' + 'A '.repeat(9990));
  check(junk.kind === 'damaged' && Date.now() - t0 < 1000, 'a 20,000-character paste of short words after CY1- reads as damaged, quickly', (Date.now() - t0) + ' ms');
  // the worst case: one-character words picked so that every word end passes the check character
  const mul = x => { let r = 0, y = 30; while (y) { if (y & 1) r ^= x; y >>= 1; x <<= 1; if (x & 32) x ^= 37; } return r; };
  let crafted = 'CY1-', run = 1;
  while (crafted.length < 19990) { const c = C.A[mul(run)]; crafted += c + ' '; run = mul(run) ^ C.A.indexOf(c); }
  const t1 = Date.now(), cr = C.read(crafted), ms = Date.now() - t1;
  check(cr.kind !== 'long' && ms < 1000, 'a crafted 20,000-character paste where every word end passes the check reads in well under a second', crafted.length + ' characters, ' + ms + ' ms, ' + cr.kind);
}

// 4c. collect(): two keys that claim one g leave that g out, held entries for it included
{
  const store = o => ({ length: Object.keys(o).length, key: i => Object.keys(o)[i], getItem: k => (Object.prototype.hasOwnProperty.call(o, k) ? o[k] : null) });
  const r = (k, gg, s) => JSON.stringify({ v: 1, g: gg, k, s });
  const held = JSON.stringify({ v: 1, held: { 12: '22', 40: '0201', 3: '1' } });
  const a = C.collect(store({ 't4t.done.net-drills.trouble-tickets': r('net-drills.trouble-tickets', 12, '12'), 't4t.done.lockdown-drills.windows-server': r('lockdown-drills.windows-server', 3, '02'), 't4t.done.held': held }));
  check(!a.clash && same(a.rec, { 3: '12', 12: '22', 40: '0201' }), 'held entries merge into their records by maximum (control)', JSON.stringify(a.rec));
  const b = C.collect(store({ 't4t.done.net-drills.trouble-tickets': r('net-drills.trouble-tickets', 12, '12'), 't4t.done.net-drills.config-audit': r('net-drills.config-audit', 12, '2222'),
    't4t.done.lockdown-drills.windows-server': r('lockdown-drills.windows-server', 3, '02'), 't4t.done.held': held }));
  check(b.clash && same(b.rec, { 3: '12', 40: '0201' }), 'two keys that claim one g leave it out, and a held entry for that g stays out too', JSON.stringify(b.rec));
}

// 5. Structure: a valid check character over a broken bit layout still reads as damaged
{
  // k: the segment count written first (Elias-gamma of k + 1); bits: everything after it
  const gam = v => { const s = v.toString(2); return Array(s.length - 1).fill(0).concat(s.split('').map(Number)); };
  const fromBits = (bits, k) => {
    const b = gam((k === undefined ? 1 : k) + 1).concat(bits); while (b.length % 5) b.push(0);
    let o = ''; for (let i = 0; i < b.length; i += 5) o += C.A[b[i] * 16 + b[i + 1] * 8 + b[i + 2] * 4 + b[i + 3] * 2 + b[i + 4]];
    return 'CY1-' + o + C.check('1' + o);
  };
  const dense = s => [].concat(...s.split('').map(c => c === '0' ? [0] : [1, c === '2' ? 1 : 0]));
  const seg = (dg, s) => gam(dg).concat(gam(s.length), [0], dense(s));
  const good = seg(3, '2120012'), head = gam(2).length;
  check(C.read(fromBits(good)).kind === 'ok' && C.read(fromBits(good.concat(seg(2, '12')), 2)).kind === 'ok', 'hand-built valid layouts read (control)');
  const padded = good.concat(Array(5 - (head + good.length) % 5 + 5).fill(0));
  check(C.read(fromBits(padded)).kind === 'damaged', 'padding of 5 or more bits is damaged');
  const onePad = good.slice(); while ((head + onePad.length) % 5 !== 4) onePad.push(0); onePad.push(1);
  check((head + onePad.length) % 5 === 0 && C.read(fromBits(onePad)).kind === 'damaged', 'padding with a 1 in it is damaged');
  check(C.read(fromBits(good, 2)).kind === 'damaged' && C.read(fromBits(good.concat(seg(2, '12')), 1)).kind === 'damaged', 'a segment count that differs from the segments is damaged');
  check(C.read(fromBits(good, 0)).kind === 'damaged' && C.read(fromBits([], 0)).kind === 'damaged', 'a segment count of 0 with a payload is damaged (the empty code has no payload)');
  check(C.read(fromBits(gam(2).concat(gam(5), [1, 1, 0], gam(9)))).kind === 'damaged', 'a run past n is damaged');
  check(C.read(fromBits(gam(2).concat(gam(5), [1, 1, 1], gam(5)))).kind === 'damaged', 'a first run of state 3 is damaged');
  check(C.read(fromBits(seg(64, '2'))).kind === 'damaged' && C.read(fromBits(seg(40, '2').concat(seg(24, '2')))).kind === 'damaged', 'g over 63 is damaged');
  check(C.read(fromBits(Array(12).fill(0).concat([1], Array(12).fill(0), seg(1, '2')))).kind === 'damaged', 'a g of 0 (no 1 bit within 12 bits) is damaged');
  check(C.read(fromBits(gam(1).concat(gam(4096), [0], dense('2'.repeat(4096))))).kind === 'damaged', 'n over 4095 is damaged');
  check(C.read(fromBits(seg(1, '2120')).slice(0)).kind === 'damaged', 'a segment ending in an untouched slot is damaged');
  check(C.read(fromBits(seg(1, '000'))).kind === 'damaged', 'an all-zero segment is damaged');
  check(C.read(fromBits(gam(1).concat(gam(20), [0], [1, 1, 1, 1]))).kind === 'damaged', 'bits that run out mid-segment are damaged');
  const big = C.encode({ 4: '2'.repeat(400) });
  check(C.read(big, { 4: 143 }).kind === 'damaged' && C.read(big, { 4: 144 }).kind === 'ok' && C.read(big).kind === 'ok', 'on a page that knows the segment, n over its slots plus 256 is damaged');
}

// 6. Mode choice and lengths
{
  const modeBit = rec => { const c = C.encode(rec).slice(4, -1), bits = []; for (const ch of c) { const v = C.A.indexOf(ch); for (let k = 4; k >= 0; k--) bits.push((v >> k) & 1); }
    let p = 0; const gm = () => { let z = 0; while (!bits[p++]) z++; let v = 1; while (z--) v = v * 2 + bits[p++]; return v; }; gm(); gm(); gm(); return bits[p]; };
  check(modeBit({ 1: '2'.repeat(300) }) === 1 && modeBit({ 1: states(300, 'alt') }) === 0, 'the encoder picks runs for long runs and dense for alternating states');
  let shorter = 0;
  for (let k = 0; k < 300; k++) {
    const s = states(1 + Math.floor(rnd() * 600), rnd() < 0.5 ? 'runs' : 'mix').replace(/0+$/, '') || '2', m = modeBit({ 1: s }), len = C.encode({ 1: s }).length;
    const d = 4 + 1 + Math.ceil((gam1(2) + gam1(1) + gam1(s.length) + 1 + s.length + (s.match(/[12]/g) || []).length) / 5);
    if ((m === 0 && len === d) || (m === 1 && len <= d)) shorter++;
  }
  function gam1(v) { return 2 * Math.floor(Math.log2(v)) + 1; }
  check(shorter === 300, 'each segment takes the shorter mode', shorter + ' of 300');
  // section 3's table, rebuilt with the same generator (simulate.js) and the CLI Lab's 182 tasks
  let s7 = 7; const r7 = () => (s7 = (s7 * 1103515245 + 12345) % 2147483648) / 2147483648;
  const seg = (n, touched, pRight, clustered) => { let s = ''; for (let i = 0; i < n; i++) { const t = clustered ? i < touched : r7() < touched / n; s += t ? (r7() < pRight ? '2' : '1') : '0'; } return s; };
  const all = p => Object.fromEntries(Object.entries(SEG).map(([g, n]) => [g, seg(n, n, p, true)]));
  const cases = [
    ['nothing yet', {}, 5],
    ['beginner', { 1: seg(662, 150, 0.85, true), 2: seg(84, 30, 0.9, true), 7: seg(140, 21, 0.86, true) }, 52],
    ['middle', { 1: seg(662, 330, 0.8, true), 2: seg(84, 60, 0.85, true), 3: seg(92, 40, 0.85, true), 4: seg(71, 50, 0.8, true), 7: seg(140, 89, 0.8, true), 8: seg(117, 40, 0.8, true), 10: seg(182, 40, 1, true), 12: seg(67, 30, 0.7, false) }, 184],
    ['every item, 85% right', all(0.85), 381],
    ['every item, 97% right', all(0.97), 175],
    ['every item, half right', all(0.5), 600],
  ];
  const lines = cases.map(([name, rec, want]) => { const n = C.encode(rec).length; return [name, n, want, Math.abs(n - want) <= Math.max(1, want * 0.1)]; });
  check(lines.every(x => x[3]), 'code lengths are within 10% of the spec table', lines.map(x => x[0] + ' ' + x[1] + ' (table ' + x[2] + ')').join('; '));
  const top =C.encode(Object.fromEntries(Object.entries(SEG).map(([g, n]) => [g, states(n, 'alt')]))).length;
  check(top <= 740, 'the longest code at today\'s counts stays near 710 characters', top + ' characters');
}

// 7. Words: no rounding call (Math.floor(x + 0.5) does that job), and the kit's page-word check passes over the codec
{
  const rounding = new RegExp('Math\\.' + 'r' + 'ound');
  check(!rounding.test(src), 'the codec calls no Math rounding function by name');
  const kit = process.env.T4T_WORD_CHECK || path.join(ROOT, '..', 'tool4that-src-dlbackup', 'curriculum', 'build_study_map.py');
  if (fs.existsSync(kit)) {
    const py = fs.readFileSync(kit, 'utf8'), m = py.match(/^BANNED = re\.compile\(((?:\s*r"[^"]*")+)\s*,\s*re\.I\)/m);
    if (m) {
      const words = new RegExp(m[1].match(/r"([^"]*)"/g).map(x => x.slice(2, -1)).join(''), 'i');
      check(!words.test(src), 'the codec passes the kit\'s page-word check', (src.match(words) || [''])[0]);
      check(!words.test(fs.readFileSync(__filename, 'utf8')), 'this test file passes it too');
    } else check(false, 'the kit\'s page-word check is readable', kit);
  } else console.log('SKIP  the kit\'s page-word check (' + kit + ' is not on this computer)');
}

console.log((fails ? 'FAILED' : 'PASSED') + ': ' + passes + ' passed, ' + fails + ' failed');
process.exit(fails ? 1 : 0);
