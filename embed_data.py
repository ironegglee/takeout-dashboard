"""将 data.json 嵌入 index.html，解决 file:// 协议下 fetch() 被浏览器 CORS 拦截问题。
幂等版本：可重复运行，不会重复嵌入。
每次运行自动更新 build-time 和 VER 缓存版本。
运行：python embed_data.py
"""
import json, os
from datetime import datetime

DATA_JSON = os.path.join(os.path.dirname(__file__), 'dashboard', 'data.json')
INDEX_HTML = os.path.join(os.path.dirname(__file__), 'index.html')

# ═══════════════════════════════════════════
# 1. 读取 data.json
# ═══════════════════════════════════════════
with open(DATA_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'data.json: {len(data.get("mt_stores",[]))}MT + {len(data.get("mp_stores",[]))}MP')

# ═══════════════════════════════════════════
# 1a. 读取 dashboard/index.html 提取当前版本号
# ═══════════════════════════════════════════
SRC_HTML = os.path.join(os.path.dirname(__file__), 'dashboard', 'index.html')
with open(SRC_HTML, 'r', encoding='utf-8') as f:
    src_html = f.read()

import re
ver_match = re.search(r'<meta name="version" content="([^"]+)"', src_html)
CURRENT_VERSION = ver_match.group(1) if ver_match else 'v2.9.0'
print(f'当前版本: {CURRENT_VERSION}')

# 提取日期范围
# 提取日期范围
full_date = data.get('full_date_range', data.get('mp_date_range', ''))
date_start = '2026-05-01'
date_end = '2026-06-02'

# 优先从 mp_daily + mt_daily + perf_daily 真实数据计算日期范围
all_dates = set()
for arr_key in ('mp_daily', 'mt_daily', 'perf_daily', 'order_daily'):
    for d in data.get(arr_key, []):
        dt = d.get('date', '')
        if dt: all_dates.add(dt)
if all_dates:
    sorted_dates = sorted(all_dates)
    date_start = sorted_dates[0]
    date_end = sorted_dates[-1]
    print(f'数据日期范围: {date_start} ~ {date_end}')
elif full_date and ' ~ ' in full_date:
    parts = full_date.split(' ~ ')
    date_start = parts[0].strip()
    date_end = parts[1].strip()

# ═══════════════════════════════════════════
# 2. 读取 index.html
# ═══════════════════════════════════════════
with open(INDEX_HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# ═══════════════════════════════════════════
# 3. 注入 EMBEDDED_DATA（幂等：用边界替换）
# ═══════════════════════════════════════════

MARKER_START = 'let REAL_MP_SUMMARY = null;'
MARKER_END = 'const STORE_MP = ['

if MARKER_START not in html:
    print('ERROR: 找不到 MARKER_START')
    exit(1)
if MARKER_END not in html:
    print('ERROR: 找不到 MARKER_END')
    exit(1)

# 查找边界
idx_start = html.index(MARKER_START)
idx_end = html.index(MARKER_END, idx_start)

new_block = MARKER_START + f'''

/* ================================================================
   嵌入真实数据（由 embed_data.py 自动生成）
   绕过 file:// 协议下 fetch() 的浏览器 CORS 限制
================================================================ */
const EMBEDDED_DATA = {json.dumps(data, ensure_ascii=False)};
const EMBEDDED_DATE_START = "{date_start}";
const EMBEDDED_DATE_END = "{date_end}";
   // 真实汇总 {{total_orders,avg_cook_time,达标率}}

'''

html = html[:idx_start] + new_block + html[idx_end:]

# ═══════════════════════════════════════════
# 4. 修复 init() 函数（幂等）
# ═══════════════════════════════════════════

# 如果存在 fetch 调用，替换为直接使用 EMBEDDED_DATA
if "fetch('data.json" in html or 'fetch("data.json' in html:
    old_fetch_block = """  function doRender(){
    const as=document.getElementById('gf-area-mgr');
    const allAm=[...new Set([...STORE_MP,...STORE_MT].map(s=>s.area_mgr).filter(Boolean))];
    as.innerHTML='<option value="all">全部区经理</option>'+allAm.map(a=>`<option value="${a}">${a}</option>`).join('');
    rebuildMarketBrandSelect();
    rebuildCitySelect();
    renderSummaryTags();
    render('today');
  }

  // 尝试加载真实数据
  fetch('data.json?t=' + Date.now())
    .then(r => r.ok ? r.json() : Promise.reject('HTTP '+r.status))
    .then(data => {
      applyRealData(data);
      doRender();
    })
    .catch(err => {
      console.warn('[看板] 真实数据加载失败，使用演示数据。错误:', err);
      const info = document.getElementById('data-info-bar');
      if(info) info.innerHTML = `<span style="color:#A32D2D;font-weight:500">⚠ 数据加载失败（${err}），当前为演示数据。请检查 data.json 文件是否有效。</span>`;
      doRender();
    });
})();"""

    new_fetch_block = """  applyRealData(EMBEDDED_DATA);

  function doRender(){
    const as=document.getElementById('gf-area-mgr');
    const allAm=[...new Set([...STORE_MP,...STORE_MT].map(s=>s.area_mgr).filter(Boolean))];
    as.innerHTML='<option value="all">全部区经理</option>'+allAm.map(a=>`<option value="${a}">${a}</option>`).join('');
    rebuildMarketBrandSelect();
    rebuildCitySelect();
    renderSummaryTags();
    render('today');
  }

  doRender();
})();"""

    if old_fetch_block in html:
        html = html.replace(old_fetch_block, new_fetch_block)
        print('已替换 fetch → EMBEDDED_DATA')

# 修复日期初始值（如果仍是硬编码 new Date()）
old_date_init = """(function init(){
  const n=new Date(),p=t=>String(t).padStart(2,'0'),fmt=d=>`${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
  const st7=new Date(n);st7.setDate(n.getDate()-6);
  document.getElementById('gf-date-start').value=fmt(st7);
  document.getElementById('gf-date-end').value=fmt(n);
  gfState.dateStart=fmt(st7);gfState.dateEnd=fmt(n);"""

if old_date_init in html:
    new_date_init = f"""(function init(){{
  const p=t=>String(t).padStart(2,'0'),fmt=d=>`${{d.getFullYear()}}-${{p(d.getMonth()+1)}}-${{p(d.getDate())}}`;
  // 默认显示最新单日
  document.getElementById('gf-date-start').value=EMBEDDED_DATE_END;
  document.getElementById('gf-date-end').value=EMBEDDED_DATE_END;
  gfState.dateStart=EMBEDDED_DATE_END;gfState.dateEnd=EMBEDDED_DATE_END;

  // 标题栏数据更新日期
  const hd = document.getElementById('headerUpdateDate');
  if(hd) hd.textContent = '数据更新至 ' + EMBEDDED_DATE_END;"""
    html = html.replace(old_date_init, new_date_init)
    print('已替换日期初始值 → EMBEDDED_DATE')

# ═══════════════════════════════════════════
# 5. 更新 build-time 和 VER（每次运行自动更新）
# ═══════════════════════════════════════════
now = datetime.now()
build_time = now.strftime('%Y-%m-%dT%H:%M:%S+08:00')
ver_str = f'{CURRENT_VERSION}@{now.strftime("%Y%m%d")}'

html = html.replace('__BUILD_TIME__', build_time)
html = html.replace('__VER__', ver_str)
print(f'build-time: {build_time}')
print(f'VER: {ver_str}')

# ═══════════════════════════════════════════
# 6. 写入
# ═══════════════════════════════════════════
with open(INDEX_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

fsize = len(html) / 1024
print(f'\nindex.html: {fsize:.0f} KB')
print(f'日期范围: {date_start} ~ {date_end}')
print('完成！')
