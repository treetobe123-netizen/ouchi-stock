// おうちストック — Googleスプレッドシート保存用API
// 1. スプレッドシートの「拡張機能 > Apps Script」にこのファイルを貼り付けて保存
// 2. 関数「setup」を一度だけ実行（権限を許可）→ 実行ログに「合言葉」が出る
// 3. 「デプロイ > 新しいデプロイ > ウェブアプリ」
//    次のユーザーとして実行: 自分 / アクセスできるユーザー: 全員

const SHEET = 'items';
const COLS = ['id', 'name', 'category', 'size', 'count', 'threshold', 'unit', 'store', 'price', 'url', 'memo', 'updatedBy', 'updatedAt'];
const NUMS = ['count', 'threshold', 'updatedAt'];

function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET);
  if (!sh) sh = ss.insertSheet(SHEET);
  if (sh.getLastRow() === 0) {
    sh.appendRow(COLS);
    sh.setFrozenRows(1);
    const now = Date.now();
    const seed = [
      ['オヤスミマン BIGサイズ以上', 'diaper', 'BIG', 3, 'パック', '夜用パンツ'],
      ['ムーニー マシュマロ肌ごこち 紙おむつ テープ', 'diaper', '', 2, 'パック', ''],
      ['パンパース おやすみパンツ Mサイズ 5-12kg', 'diaper', 'M', 3, 'パック', ''],
      ['パンパース はじめての肌へのいちばん テープ', 'diaper', '', 2, 'パック', ''],
      ['明治ほほえみ らくらくキューブ', 'milk', '', 2, '箱', ''],
      ['森永 E赤ちゃん エコらくパック', 'milk', '', 2, '箱', ''],
      ['森永 はぐくみ エコらくパック', 'milk', '', 1, '箱', ''],
    ];
    seed.forEach(s => sh.appendRow([Utilities.getUuid(), s[0], s[1], s[2], s[3], 1, s[4], '楽天24', '', '', s[5], '', now]));
  }
  const props = PropertiesService.getScriptProperties();
  let key = props.getProperty('KEY');
  if (!key) {
    key = Utilities.getUuid().replace(/-/g, '').slice(0, 16);
    props.setProperty('KEY', key);
  }
  Logger.log('合言葉: ' + key);
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function authorized(key) {
  const k = PropertiesService.getScriptProperties().getProperty('KEY');
  return !!k && key === k;
}

function sheet() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET);
}

function rev() {
  return Number(PropertiesService.getScriptProperties().getProperty('REV')) || 0;
}

function bumpRev() {
  const r = rev() + 1;
  PropertiesService.getScriptProperties().setProperty('REV', String(r));
  return r;
}

// 各行の実際の行番号(_row)も持たせる。シート途中に空行があってもずれない
function readItems(sh) {
  const values = sh.getDataRange().getValues();
  const head = values.shift() || [];
  const list = [];
  values.forEach((r, n) => {
    if (!r[0]) return;
    const o = { _row: n + 2 };
    head.forEach((h, i) => { o[h] = r[i]; });
    NUMS.forEach(k => { o[k] = Number(o[k]) || 0; });
    o.price = o.price === '' || o.price === null ? null : Number(o.price);
    ['id', 'name', 'category', 'size', 'unit', 'store', 'url', 'memo', 'updatedBy'].forEach(k => { o[k] = String(o[k] ?? ''); });
    list.push(o);
  });
  return list;
}

function publicItems(items) {
  return items.map(i => { const o = Object.assign({}, i); delete o._row; return o; });
}

function toRow(o) {
  return COLS.map(c => {
    const v = o[c];
    if (c === 'price') return v === null || v === undefined || v === '' ? '' : Number(v);
    if (NUMS.includes(c)) return Number(v) || 0;
    // 先頭が = + - @ の文字列は数式として解釈されないようにする
    const s = String(v ?? '');
    return /^[=+\-@]/.test(s) ? "'" + s : s;
  });
}

const int = (v, max) => Math.min(max, Math.max(0, Math.round(Number(v) || 0)));
const str = (v, max) => String(v ?? '').trim().slice(0, max);

// 受け取った項目を検証して整える（渡された項目だけ）
function clean(d) {
  const o = {};
  if (!d) return o;
  if ('name' in d) o.name = str(d.name, 200);
  if ('category' in d) o.category = str(d.category, 40) || 'other';
  if ('size' in d) o.size = str(d.size, 40);
  if ('unit' in d) o.unit = str(d.unit, 10) || '個';
  if ('store' in d) o.store = str(d.store, 100);
  if ('memo' in d) o.memo = str(d.memo, 1000);
  if ('url' in d) { const u = str(d.url, 2000); o.url = /^https?:\/\//i.test(u) ? u : ''; }
  if ('price' in d) o.price = d.price === null || d.price === '' || !(Number(d.price) >= 0) ? null : Number(d.price);
  if ('count' in d) o.count = int(d.count, 9999);
  if ('threshold' in d) o.threshold = int(d.threshold, 999);
  return o;
}

function doGet(e) {
  if (!authorized(e.parameter.key)) return out({ ok: false, code: 'unauthorized' });
  return out({ ok: true, rev: rev(), items: publicItems(readItems(sheet())) });
}

function doPost(e) {
  let req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return out({ ok: false, code: 'bad_request' }); }
  if (!authorized(req.key)) return out({ ok: false, code: 'unauthorized' });
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(15000)) return out({ ok: false, code: 'busy' });
  try {
    const sh = sheet();
    const cache = CacheService.getScriptCache();
    const opKey = req.op ? 'op:' + String(req.op).slice(0, 80) : '';
    // 同じ操作の再送（電波が悪くて応答だけ届かなかった場合）は二重に反映しない
    if (opKey && cache.get(opKey)) return out({ ok: true, rev: rev(), items: publicItems(readItems(sh)) });

    let items = readItems(sh);
    const by = str(req.by, 20);
    const now = Date.now();
    const find = id => items.find(i => i.id === String(id));

    if (req.action === 'add') {
      const id = str(req.id, 80) || Utilities.getUuid();
      if (!find(id)) {
        const o = Object.assign({ name: '', category: 'other', size: '', count: 0, threshold: 1, unit: '個', store: '', price: null, url: '', memo: '' }, clean(req.data));
        if (!o.name) return out({ ok: false, code: 'bad_request' });
        o.id = id; o.updatedBy = by; o.updatedAt = now;
        sh.appendRow(toRow(o));
      }
    } else if (req.action === 'adjust' || req.action === 'update' || req.action === 'delete') {
      const cur = find(req.id);
      if (!cur) return out({ ok: false, code: 'not_found', rev: rev(), items: publicItems(items) });
      if (req.action === 'delete') {
        sh.deleteRow(cur._row);
      } else {
        const o = Object.assign({}, cur, req.action === 'update' ? clean(req.data) : {});
        if (!o.name) return out({ ok: false, code: 'bad_request' });
        // 在庫数は「差分」で足す。2人が同時に＋を押しても両方反映される
        const delta = Math.round(Number(req.delta) || 0);
        if (delta) o.count = int(cur.count + delta, 9999);
        o.updatedBy = by; o.updatedAt = now;
        sh.getRange(cur._row, 1, 1, COLS.length).setValues([toRow(o)]);
      }
    } else {
      return out({ ok: false, code: 'bad_request' });
    }
    SpreadsheetApp.flush();
    const r = bumpRev();
    if (opKey) cache.put(opKey, '1', 21600);
    return out({ ok: true, rev: r, items: publicItems(readItems(sh)) });
  } catch (err) {
    return out({ ok: false, code: 'server' });
  } finally {
    lock.releaseLock();
  }
}
