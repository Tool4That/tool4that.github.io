/* The Cyber progress code, format CY1: one text that carries a learner's right and to-retry results from every Cyber
   tool. Public and data-free; ES5 (var only), so the oldest browsers the tools support read it.

   Records: { g: "0120..." }, one digit per slot in the tool's registry order: 0 untouched, 1 to retry, 2 right.
   Code: "CY1-" + payload + one check character, in Crockford base32 (0-9 and A-Z without I, L, O, and U), 5 bits per
   character, most significant bit first. With no marks at all the payload is empty, so the code is "CY1-Y".
   Otherwise the payload's bits are:
     Elias-gamma(k + 1), where k is the number of segments that follow (1 to 63), so a code cut short always fails;
     then for each segment with a mark, in ascending g:
       Elias-gamma(g - previous g) (the previous g starts at 0) and Elias-gamma(n), the slots it carries (1 to 4095);
       one mode bit, then the states: dense (per slot, 1 bit touched, then 1 bit right) or runs (the first run's state
       in 2 bits, each later run 1 bit for which of the two other states, lower first; every run followed by
       Elias-gamma(length)), whichever is shorter (dense on a tie);
     then zero bits to fill the last character (at most 4).
   Check character: a weighted check over GF(32) (polynomial x^5 + x^2 + 1, weight 30): r = 0, then r = 30*r XOR symbol
   for each symbol of "1" + payload, and the check is 30*r. It catches every single changed character and every swap
   of two neighboring characters (a plain Luhn mod 32 lets a swapped "0Z" pair through).

   Two marked parts:
   - encode: the exact text of CODE_ENC in prepare_tool.py, which every Cyber tool page's site bar carries. It defines
     T4T_CODE = { A, check(symbols) -> check character, trim, encode(records) -> "CY1-...", group(code) -> groups of
     five, rec(key, raw) -> {g, s} or null (one t4t.done.<k> value checked), held(raw) -> {g: digits}
     (t4t.done.held), max(a, b) (per-slot maximum), collect(storage) -> {rec: {g: digits}, clash: bool} (every valid
     record with held entries merged in; two keys that claim one g are both left out, along with any held entry for
     that g, and clash is true) }.
     prepare_tool.py --check-codec confirms the two copies match byte for byte.
   - decode: My Cyber progress carries it after the encode part. T4T_CODE.read(text, known) finds the code inside a
     longer paste: it drops soft hyphens and zero-width characters (U+00AD, U+200B to U+200D, U+2060, U+FEFF) and the
     "> " marks of a quoted email, reads O as 0 and I or L as 1, and drops spaces, line breaks, and hyphens after CY1-.
     When the whole run of letters and digits after CY1- fails, it tries shorter runs that end where a word ends,
     longest first, and takes the first that passes the check character and the structure (so words after the code,
     such as a sign-off, read). A shorter run never stops between two groups of a grouped code (a word of five
     characters, then a word of one to five code characters, both in one letter case or with digits only on one
     side), so a code with one typo never reads as the start of a code. Words in both cases, such as the names Kate
     and Ty, never count as a group, so they read; only a short upper-case word of code characters, or a number,
     right after a last group of five (such as "7TT2M THX") reads as damaged. It gives one of
       {kind: "ok", records: {g: digits}}   a valid code (records are empty for "CY1-Y")
       {kind: "damaged"}                    a typo, a missing piece, or a broken structure
       {kind: "newer"}                      CY2- or later: a newer version of the course
       {kind: "dl"}                         a Defense Ladder code (DL1-), and no CY1- code
       {kind: "other"}                      any other text
       {kind: "long"}                       a paste over 20,000 characters
     known (optional): {g: slot count} for the segments the page knows; a code whose n tops a known count by more
     than 256 reads as damaged. */
/*@encode*/
var T4T_CODE=(function(){var A='0123456789ABCDEFGHJKMNPQRSTVWXYZ',has=Object.prototype.hasOwnProperty;
function mul(x){var r=0,y=30;while(y){if(y&1)r^=x;y>>=1;x<<=1;if(x&32)x^=37;}return r;}
function check(s){var r=0,i;for(i=0;i<s.length;i++)r=mul(r)^A.indexOf(s.charAt(i));return A.charAt(mul(r));}
function trim(s){return String(s).replace(/0+$/,'');}
function seg(g,s){return typeof g==='number'&&g===Math.floor(g)&&g>=1&&g<=63&&typeof s==='string'&&/^[012]*$/.test(s)&&trim(s).length<=4095;}
function gam(b,v){var s=v.toString(2),i;for(i=1;i<s.length;i++)b.push(0);for(i=0;i<s.length;i++)b.push(s.charAt(i)==='1'?1:0);}
function dense(s){var b=[],i,c;for(i=0;i<s.length;i++){c=s.charAt(i);b.push(c==='0'?0:1);if(c!=='0')b.push(c==='2'?1:0);}return b;}
function runs(s){var b=[],i=0,j,c,p=-1;while(i<s.length){c=+s.charAt(i);j=i;while(j<s.length&&+s.charAt(j)===c)j++;if(p<0)b.push(c>>1,c&1);else b.push(c>3-p-c?1:0);gam(b,j-i);p=c;i=j;}return b;}
function encode(rec){var b=[],gs=[],k,i,s,d,r,p=0,o='';
for(k in rec)if(has.call(rec,k)&&/^[1-9]\d?$/.test(k)&&seg(+k,rec[k])&&trim(rec[k]))gs.push(+k);
gs.sort(function(x,y){return x-y;});
if(gs.length)gam(b,gs.length+1);
for(i=0;i<gs.length;i++){s=trim(rec[gs[i]]);gam(b,gs[i]-p);p=gs[i];gam(b,s.length);d=dense(s);r=runs(s);b.push(r.length<d.length?1:0);b=b.concat(r.length<d.length?r:d);}
while(b.length%5)b.push(0);
for(i=0;i<b.length;i+=5)o+=A.charAt(b[i]*16+b[i+1]*8+b[i+2]*4+b[i+3]*2+b[i+4]);
return 'CY1-'+o+check('1'+o);}
function group(c){return c.slice(0,4)+c.slice(4).replace(/(.{5})(?=.)/g,'$1 ');}
function rec(key,raw){var o;try{o=JSON.parse(raw);}catch(e){return null;}
return o&&o.v===1&&typeof o.k==='string'&&'t4t.done.'+o.k===key&&seg(o.g,o.s)?{g:o.g,s:trim(o.s)}:null;}
function held(raw){var o,h,k,out={};try{o=JSON.parse(raw);}catch(e){return out;}h=o&&o.v===1?o.held:null;
if(h&&typeof h==='object')for(k in h)if(has.call(h,k)&&/^[1-9]\d?$/.test(k)&&seg(+k,h[k])&&trim(h[k]))out[k]=trim(h[k]);return out;}
function max(a,b){var o='',i,x,y,n=Math.max(a.length,b.length);for(i=0;i<n;i++){x=a.charAt(i)||'0';y=b.charAt(i)||'0';o+=x>y?x:y;}return trim(o);}
function collect(ls){var r={},by={},bad={},clash=false,i,k,v,h,g,n=ls.length;
for(i=0;i<n;i++){k=ls.key(i);if(k==null||k==='t4t.done.held'||!/^t4t\.done\.[a-z0-9.-]+$/.test(k))continue;v=rec(k,ls.getItem(k));if(!v)continue;
if(has.call(by,v.g)){clash=true;bad[v.g]=1;}else{by[v.g]=k;r[v.g]=v.s;}}
for(g in bad)if(has.call(bad,g))delete r[g];
h=held(ls.getItem('t4t.done.held'));for(g in h)if(has.call(h,g)&&!has.call(bad,g))r[g]=has.call(r,g)?max(r[g],h[g]):h[g];
return {rec:r,clash:clash};}
return {A:A,check:check,trim:trim,encode:encode,group:group,rec:rec,held:held,max:max,collect:collect};})();
/*@/encode*/
/*@decode*/
(function(C){
var A=C.A,has=Object.prototype.hasOwnProperty;
function mul(x){var r=0,y=30;while(y){if(y&1)r^=x;y>>=1;x<<=1;if(x&32)x^=37;}return r;}
// the records a payload holds, or null when its structure is broken
function parse(pay,known){
  var nb=pay.length*5,i,j,k,p=0,g=0,n,s,c,q,L,out={};
  // bits are read one at a time as needed, so a long paste that breaks early costs little
  function rd(){if(p>=nb)throw 0;var x=A.indexOf(pay.charAt((p-p%5)/5)),y=(x>>(4-p%5))&1;p++;return y;}
  function gm(top){var z=0,y=1;while(!rd())if(++z>12)throw 0;while(z--)y=y*2+rd();if(y>top)throw 0;return y;}
  try{
    if(pay){
      k=gm(64)-1;if(k<1)throw 0;
      for(j=0;j<k;j++){
        g+=gm(63);if(g>63)throw 0;
        n=gm(4095);if(known&&has.call(known,g)&&n>known[g]+256)throw 0;
        s='';
        if(!rd()){while(s.length<n)s+=rd()?(rd()?'2':'1'):'0';}
        else{q=-1;while(s.length<n){if(q<0){c=rd()*2+rd();if(c>2)throw 0;}else c=rd()?(q===2?1:2):(q===0?1:0);L=gm(4095);if(s.length+L>n)throw 0;for(i=0;i<L;i++)s+=c;q=c;}}
        if(!/[12]/.test(s)||/0$/.test(s))throw 0;
        out[g]=s;
      }
      if(nb-p>4)throw 0;
      while(p<nb)if(rd())throw 0;
    }
  }catch(e){return null;}
  return out;
}
// a word's letter case: 0 digits only, 1 upper case only, 2 lower case only, 3 both (a name such as Kate, never a group)
function kase(s){var up=/[A-Z]/.test(s),lo=/[a-z]/.test(s);return up?(lo?3:1):lo?2:0;}
// may a shorter run stop between word a and the next word b? Not when they look like two groups of one code: a has
// five characters and b one to five code characters, in the same letter case or with digits only on one side
function stop(a,b){if(a.length!==5||!/^[0-9A-HJKMNP-TV-Z]{1,5}$/i.test(b))return true;var x=kase(a),y=kase(b);return y===3||x+y===3&&x!==3&&x*y>0;}
C.read=function(text,known){
  var t=text==null?'':String(text),u,m,v,w,ws=[],body='',ends=[],bad=-1,P=[1],i,j,x,out;
  if(t.length>20000)return {kind:'long'};
  u=t.replace(/[\u00ad\u200b-\u200d\u2060\ufeff]/g,'').replace(/(^|[\r\n])[ \t]*(?:>[ \t]?)+/g,'$1').replace(/[\u2010-\u2015\u2212]/g,'-');
  m=/(^|[^0-9A-Z.])CY[ \t]*([0-9OIL]+)[ \t]*-/i.exec(u);
  if(!m)return /(^|[^0-9A-Z.])DL\d+-/i.test(u)?{kind:'dl'}:{kind:'other'};
  v=+m[2].toUpperCase().replace(/O/g,'0').replace(/[IL]/g,'1');
  if(v!==1)return {kind:v>1?'newer':'damaged'};
  // the words after CY1- (letters, digits, and hyphens), joined; ends: where each word ends in the joined text
  w=/^[0-9A-Z\s-]*/i.exec(u.slice(m.index+m[0].length))[0].split(/\s+/);
  for(i=0;i<w.length;i++){x=w[i].replace(/-+/g,'');if(x){ws.push(x);body+=x.toUpperCase().replace(/O/g,'0').replace(/[IL]/g,'1');ends.push(body.length);}}
  if(!body)return {kind:'damaged'};
  // P[i]: the check's running value over "1" and the first i characters, up to the first character outside the alphabet
  for(i=0;i<body.length;i++){x=A.indexOf(body.charAt(i));if(x<0){bad=i;break;}P.push(mul(P[i])^x);}
  // the whole run first, then shorter runs that end where a word ends, longest first; a shorter run never stops
  // between two groups of a grouped code (see stop), so a code with one typo never reads as a shorter code. The
  // running value P equals C.check, so each candidate costs one lookup before parse.
  for(j=ends.length-1;j>=0;j--){
    i=ends[j];
    if(bad>=0&&i>bad)continue;
    if(j<ends.length-1&&!stop(ws[j],ws[j+1]))continue;
    if(A.charAt(mul(P[i-1]))!==body.charAt(i-1))continue;
    out=parse(body.slice(0,i-1),known);
    if(out)return {kind:'ok',records:out};
  }
  return {kind:'damaged'};
};
})(T4T_CODE);
/*@/decode*/
if(typeof module!=='undefined')module.exports=T4T_CODE;
