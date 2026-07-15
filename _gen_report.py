import json, os
from collections import defaultdict, Counter

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt

OUT_DIR = r'C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31\report'
os.makedirs(OUT_DIR, exist_ok=True)

with open(r'C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31\dashboard\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

alerts = data.get('alerts', [])
stores = data.get('mt_stores', [])

# ── Build store index ──
store_map = {}
for s in stores:
    store_map[s.get('name', '')] = {
        'brand': s.get('brand', ''),
        'market': s.get('market', '') or s.get('region', ''),
        'city': s.get('city', ''),
        'area_mgr': s.get('area_mgr', ''),
        'region_mgr': s.get('region_mgr', ''),
        'leader': s.get('leader', ''),
        'shop_score': s.get('shop_score', 0),
        'exp_score': s.get('exp_score', 0),
        'shop_dims': s.get('shop_dims', {}),
        'exp_dims': s.get('exp_dims', {}),
    }

# ── Store alerts ──
store_alert = defaultdict(lambda: {'cook':0,'shop':0,'exp':0,'total':0,'cook_detail':[],'shop_detail':[],'exp_detail':[]})
for a in alerts:
    sname = a.get('store', '')
    t = a.get('type', '')
    if t == 'cook':
        store_alert[sname]['cook'] += 1
        store_alert[sname]['cook_detail'].append(a)
    elif t == 'shop':
        store_alert[sname]['shop'] += 1
        store_alert[sname]['shop_detail'].append(a)
    elif t == 'rating':
        store_alert[sname]['exp'] += 1
        store_alert[sname]['exp_detail'].append(a)
    store_alert[sname]['total'] += 1

# ── Market x Brand groups ──
MKT_ORDER = ['湖南', '江苏', '湖北', '重庆']
BRAND_ORDER = ['茶颜悦色', '墨柠', '鸳央咖啡', '昼夜诗']
groups = {}
for mkt in MKT_ORDER:
    for bd in BRAND_ORDER:
        key = (mkt, bd)
        names = [n for n, s in store_map.items() if s['market'] == mkt and s['brand'] == bd]
        if not names:
            continue
        group = {'names': names, 'count': len(names)}
        # Stats
        shop_scores = [store_map[n]['shop_score'] for n in names if store_map[n]['shop_score'] > 0]
        exp_scores = [store_map[n]['exp_score'] for n in names if store_map[n]['exp_score'] > 0]
        group['avg_shop'] = sum(shop_scores) / len(shop_scores) if shop_scores else 0
        group['avg_exp'] = sum(exp_scores) / len(exp_scores) if exp_scores else 0
        group['low_shop'] = len([n for n in names if 0 < store_map[n]['shop_score'] <= 92])
        group['low_exp'] = len([n for n in names if 0 < store_map[n]['exp_score'] <= 4.3])
        group['zero_exp'] = len([n for n in names if store_map[n]['exp_score'] == 0])

        # Common dim problems
        dim_counter = Counter()
        for n in names:
            sd = store_map[n]['shop_dims']
            for dk, dv in sd.items():
                if dv is not None and dv < 90:
                    dim_counter[dk] += 1
            ed = store_map[n]['exp_dims']
            for dk, dv in ed.items():
                if dv is not None and dv < 4.2:
                    dim_counter[dk] += 1
        group['top_dims'] = dim_counter.most_common(5)

        # Alert breakdown
        alerts_total = sum(store_alert.get(n, {}).get('total', 0) for n in names)
        cook_total = sum(store_alert.get(n, {}).get('cook', 0) for n in names)
        shop_total = sum(store_alert.get(n, {}).get('shop', 0) for n in names)
        exp_total = sum(store_alert.get(n, {}).get('exp', 0) for n in names)
        group['alerts'] = alerts_total
        group['cook_alerts'] = cook_total
        group['shop_alerts'] = shop_total
        group['exp_alerts'] = exp_total

        # Tail stores (ranked by deviation)
        tail = []
        for n in names:
            sa = store_alert.get(n, {'total':0, 'cook':0, 'shop':0, 'exp':0, 'cook_detail':[], 'shop_detail':[], 'exp_detail':[]})
            sm = store_map.get(n, {})
            dev = sa['total'] * 5 + max(0, 95 - sm.get('shop_score', 95)) * 2 + max(0, 4.6 - sm.get('exp_score', 4.6)) * 50
            if dev > 0:
                tail.append((n, dev, sa, sm))
        tail.sort(key=lambda x: x[1], reverse=True)
        group['tail'] = tail[:15]

        # Area managers
        area_stats = defaultdict(lambda: {'count':0, 'alert':0, 'low_s':0, 'low_e':0, 'shop_sum':0, 'exp_sum':0})
        for n in names:
            sm = store_map[n]
            a = sm.get('area_mgr', '')
            area_stats[a]['count'] += 1
            area_stats[a]['alert'] += store_alert.get(n, {}).get('total', 0)
            if 0 < sm['shop_score'] <= 92: area_stats[a]['low_s'] += 1
            if 0 < sm['exp_score'] <= 4.3: area_stats[a]['low_e'] += 1
            if sm['shop_score'] > 0: area_stats[a]['shop_sum'] += sm['shop_score']
            if sm['exp_score'] > 0: area_stats[a]['exp_sum'] += sm['exp_score']
        group['area_rank'] = sorted(area_stats.items(), key=lambda x: x[1]['alert'] + x[1]['low_s']*3, reverse=True)[:5]

        groups[key] = group

# ── Key dimension name mapping ──
DIM_LABEL = {
    'peak_biz': '高峰营业', 'reject_rate': '拒单率', 'reply_rate': '回复率',
    'shop_rating': '商家评分', 'menu_rich': '菜单丰富', 'cook_report': '出餐上报',
    'base_biz': '基础营业', 'biz_days': '营业天数',
    'prod_quality': '商品质量', 'pack_quality': '包装', 'svc_exp': '服务体验',
    'repurchase': '复购率', 'msg_reply': '消息回复', 'svc_neg': '服务负反馈',
    'food_safety': '食品安全', 'delivery_exp': '配送体验',
}

def dim_label(k):
    return DIM_LABEL.get(k, k)

# ═══════════════════════════════════════
# CHART 1: Overview — alerts by market/brand
# ═══════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for idx, mkt in enumerate(MKT_ORDER):
    ax = axes[idx // 2][idx % 2]
    brands_in_mkt = [bd for bd in BRAND_ORDER if (mkt, bd) in groups]
    x = range(len(brands_in_mkt))
    alerts_l = [groups[(mkt, bd)]['alerts'] for bd in brands_in_mkt]
    low_s = [groups[(mkt, bd)]['low_shop'] for bd in brands_in_mkt]
    low_e = [groups[(mkt, bd)]['low_exp'] for bd in brands_in_mkt]
    w = 0.25
    bars1 = ax.bar([i - w for i in x], alerts_l, w, label='预警', color='#e74c3c')
    bars2 = ax.bar(x, low_s, w, label='低店铺分(≤92)', color='#f39c12')
    bars3 = ax.bar([i + w for i in x], low_e, w, label='低体验分(≤4.3)', color='#e67e22')
    for b in bars1:
        v = int(b.get_height())
        if v > 0: ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1, str(v), ha='center', va='bottom', fontsize=8)
    ax.set_title(mkt, fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(brands_in_mkt, fontsize=10)
    ax.legend(fontsize=7, loc='upper right')
    ax.set_ylabel('数量')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'chart_overview.png'), dpi=150, bbox_inches='tight')
plt.close()

# ═══════════════════════════════════════
# CHART 2+3: Multi-plot helper
# ═══════════════════════════════════════
group_keys = [(m, b) for m in MKT_ORDER for b in BRAND_ORDER if (m, b) in groups]
n_groups = len(group_keys)
if n_groups == 0:
    # fallback: collect all unique market-brand combos from data
    actual_mb = set()
    for s in store_map.values():
        actual_mb.add((s['market'], s['brand']))
    group_keys = sorted(actual_mb)
    n_groups = len(group_keys)
cols = min(4, max(1, n_groups))
rows = max(1, (n_groups + cols - 1) // cols)

def make_multi_axes(rows, cols):
    fig, axes = plt.subplots(rows, cols, figsize=(5.5 * cols, 4 * rows), squeeze=False)
    return fig, axes

# Chart 2: Alert type breakdown
fig2, axes2 = make_multi_axes(rows, cols)
for i, (mkt, bd) in enumerate(group_keys):
    r, c = divmod(i, cols)
    g = groups[(mkt, bd)]
    ax = axes2[r][c]
    sizes = [g['cook_alerts'], g['shop_alerts'], g['exp_alerts']]
    labels = ['出餐超时', '店铺分低', '体验分低']
    colors_2 = ['#3498db', '#e74c3c', '#f39c12']
    nz = [(l, s, cl) for l, s, cl in zip(labels, sizes, colors_2) if s > 0]
    if nz:
        ax.pie([x[1] for x in nz], labels=[x[0] for x in nz], colors=[x[2] for x in nz],
               autopct='%1.0f%%', textprops={'fontsize': 8})
    else:
        ax.text(0.5, 0.5, '无预警', ha='center', va='center', transform=ax.transAxes, fontsize=12)
    ax.set_title(f'{mkt}-{bd}', fontsize=10, fontweight='bold')
# Hide unused
for i in range(n_groups, rows * cols):
    r, c = divmod(i, cols)
    axes2[r][c].set_visible(False)
plt.tight_layout()
fig2.savefig(os.path.join(OUT_DIR, 'chart_alert_types.png'), dpi=150, bbox_inches='tight')
plt.close(fig2)

# Chart 3: Top dimension problems
fig3, axes3 = make_multi_axes(rows, cols)
for i, (mkt, bd) in enumerate(group_keys):
    r, c = divmod(i, cols)
    g = groups[(mkt, bd)]
    ax = axes3[r][c]
    dims = g['top_dims']
    if dims:
        names = [dim_label(d[0]) for d in dims]
        vals = [d[1] for d in dims]
        bars = ax.barh(range(len(names)), vals, color='#e74c3c', height=0.6)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        for b, v in zip(bars, vals):
            ax.text(b.get_width() + 0.5, b.get_y() + b.get_height()/2, str(v), va='center', fontsize=7)
    else:
        ax.text(0.5, 0.5, '无显著异常', ha='center', va='center', transform=ax.transAxes, fontsize=12)
    ax.set_title(f'{mkt}-{bd}', fontsize=10, fontweight='bold')
# Hide unused
for i in range(n_groups, rows * cols):
    r, c = divmod(i, cols)
    axes3[r][c].set_visible(False)
plt.tight_layout()
fig3.savefig(os.path.join(OUT_DIR, 'chart_dim_problems.png'), dpi=150, bbox_inches='tight')
plt.close(fig3)

# ═══════════════════════════════════════
# CHART 4: Area manager ranking (all markets)
# ═══════════════════════════════════════
all_area = defaultdict(lambda: {'count':0, 'alert':0, 'low_s':0, 'low_e':0, 'shop_sum':0, 'exp_sum':0})
for name, sm in store_map.items():
    a = sm.get('area_mgr', '')
    all_area[a]['count'] += 1
    all_area[a]['alert'] += store_alert.get(name, {}).get('total', 0)
    if 0 < sm['shop_score'] <= 92: all_area[a]['low_s'] += 1
    if 0 < sm['exp_score'] <= 4.3: all_area[a]['low_e'] += 1
    if sm['shop_score'] > 0:
        all_area[a]['shop_sum'] += sm['shop_score']
        all_area[a]['exp_sum'] += sm['exp_score']
areas_ranked = sorted(all_area.items(), key=lambda x: x[1]['alert'] + x[1]['low_s']*3 + x[1]['low_e']*2, reverse=True)
top_areas = areas_ranked[:12]

fig, ax = plt.subplots(figsize=(14, 6))
names = [a[0] for a in top_areas]
alerts_a = [a[1]['alert'] for a in top_areas]
low_s_a = [a[1]['low_s'] for a in top_areas]
low_e_a = [a[1]['low_e'] for a in top_areas]
x = range(len(names))
w = 0.25
ax.bar([i - w for i in x], alerts_a, w, label='预警数', color='#e74c3c')
ax.bar(x, low_s_a, w, label='低店铺分', color='#f39c12')
ax.bar([i + w for i in x], low_e_a, w, label='低体验分', color='#e67e22')
for i, (n, a1, s1, e1) in enumerate(zip(names, alerts_a, low_s_a, low_e_a)):
    if a1 > 0: ax.text(i - w, a1 + 0.5, str(a1), ha='center', fontsize=7)
    if s1 > 0: ax.text(i, s1 + 0.5, str(s1), ha='center', fontsize=7)
    if e1 > 0: ax.text(i + w, e1 + 0.5, str(e1), ha='center', fontsize=7)
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=8, rotation=30, ha='right')
ax.legend(fontsize=9)
ax.set_title('区经理问题密度排行 (预警+低分)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'chart_area_mgr.png'), dpi=150, bbox_inches='tight')
plt.close()

# ───────────────────────────────────────
# Build HTML
# ───────────────────────────────────────
def fmt_score(v):
    if v is None or v == 0:
        return '<span class="zero">--</span>'
    if v <= 4.3 if isinstance(v, float) and v < 10 else v <= 92:
        return f'<span class="red">{v}</span>'
    return str(v)

def dim_tag(k, v):
    label = dim_label(k)
    if v is None:
        return ''
    if k in ('prod_quality', 'pack_quality', 'svc_exp', 'repurchase', 'msg_reply', 'svc_neg', 'food_safety', 'delivery_exp'):
        threshold = 4.2
        cls = 'red' if v < threshold else ''
        return f'<span class="{cls} dim-tag">{label} {v}</span>'
    else:
        threshold = 90
        cls = 'red' if v < threshold else ''
        return f'<span class="{cls} dim-tag">{label} {v}</span>'

def gen_mb_section(mkt, bd):
    g = groups[(mkt, bd)]
    if not g['names']:
        return ''

    lines = []
    lines.append(f'<div class="section" id="{mkt}-{bd}">')
    lines.append(f'<h2>{mkt}市场 — {bd}</h2>')

    # Summary
    lines.append('<div class="summary-grid">')
    lines.append(f'<div class="stat-card"><div class="num">{g["count"]}</div><div class="label">门店数</div></div>')
    lines.append(f'<div class="stat-card"><div class="num">{g["alerts"]}</div><div class="label">预警</div></div>')
    lines.append(f'<div class="stat-card"><div class="num">{g["low_shop"]}</div><div class="label">低店铺分</div></div>')
    lines.append(f'<div class="stat-card"><div class="num">{g["low_exp"]}</div><div class="label">低体验分</div></div>')
    if g['zero_exp']:
        lines.append(f'<div class="stat-card alert"><div class="num">{g["zero_exp"]}</div><div class="label">体验分=0</div></div>')
    lines.append(f'<div class="stat-card"><div class="num">{g["avg_shop"]:.1f}</div><div class="label">均店铺分</div></div>')
    lines.append(f'<div class="stat-card"><div class="num">{g["avg_exp"]:.2f}</div><div class="label">均体验分</div></div>')
    lines.append('</div>')

    # Common problems
    if g['top_dims']:
        lines.append('<div class="problem-bar">')
        lines.append('<strong>🔴 共性问题：</strong>')
        for dk, dv in g['top_dims']:
            lines.append(f'<span class="dim-tag red">{dim_label(dk)}×{dv}店</span>')
        lines.append('</div>')

    # Tail stores table
    if g['tail']:
        lines.append('<h3>⚠️ 重点关注门店</h3>')
        lines.append('<table><thead><tr><th>排名</th><th>门店</th><th>店铺分</th><th>体验分</th><th>预警</th><th>核心病灶</th><th>负责人</th></tr></thead><tbody>')
        for rank, (name, dev, sa, sm) in enumerate(g['tail'], 1):
            # Key issues
            issues = []
            sd = sm.get('shop_dims', {})
            for k, v in sd.items():
                if v is not None and k in ('reply_rate', 'reject_rate', 'shop_rating') and v < 90:
                    issues.append(dim_tag(k, v))
            ed = sm.get('exp_dims', {})
            for k, v in ed.items():
                if v is not None and v < 4.2:
                    issues.append(dim_tag(k, v))
            if sa['cook'] > 0:
                avg_c = round(sum(d.get('avg_cook', 0) for d in sa['cook_detail']) / max(sa['cook'], 1), 1)
                issues.insert(0, f'<span class="dim-tag blue">出餐{avg_c}分</span>')

            shop_s = fmt_score(sm.get('shop_score', 0))
            exp_s = fmt_score(sm.get('exp_score', 0))
            area = sm.get('area_mgr', '')
            lines.append(f'<tr><td>{rank}</td><td><strong>{name}</strong></td><td>{shop_s}</td><td>{exp_s}</td><td>{sa["total"]}</td><td>{"".join(issues)}</td><td>{area}</td></tr>')
        lines.append('</tbody></table>')

    # Area manager rank
    if g['area_rank']:
        lines.append('<h3>📋 区经理关注</h3>')
        lines.append('<table><thead><tr><th>区经理</th><th>管店</th><th>预警</th><th>低店分</th><th>低体分</th><th>均店分</th><th>均体分</th></tr></thead><tbody>')
        for a, info in g['area_rank'][:5]:
            n = info['count']
            if n == 0: continue
            asp = info['shop_sum'] / n if n else 0
            aep = info['exp_sum'] / n if n else 0
            lines.append(f'<tr><td>{a}</td><td>{n}</td><td>{info["alert"]}</td><td class="red">{info["low_s"]}</td><td class="red">{info["low_e"]}</td><td>{asp:.1f}</td><td>{aep:.2f}</td></tr>')
        lines.append('</tbody></table>')

    lines.append('</div>')  # end section
    return '\n'.join(lines)

# ═══════════════════════════════════════
# HTML template
# ═══════════════════════════════════════
sections_html = []
for mkt in MKT_ORDER:
    for bd in BRAND_ORDER:
        if (mkt, bd) in groups:
            sections_html.append(gen_mb_section(mkt, bd))

# TOC
toc_items = []
for mkt in MKT_ORDER:
    mkt_groups = [(bd, groups[(mkt, bd)]['alerts'], groups[(mkt, bd)]['low_shop'] + groups[(mkt, bd)]['low_exp'])
                  for bd in BRAND_ORDER if (mkt, bd) in groups]
    if not mkt_groups:
        continue
    toc_items.append(f'<li class="toc-mkt">{mkt}')
    toc_items.append('<ul>')
    for bd, alerts_n, low_n in mkt_groups:
        badge = f' <span class="badge">{alerts_n}预警 {low_n}低分</span>' if alerts_n or low_n else ''
        toc_items.append(f'<li><a href="#{mkt}-{bd}">{bd}{badge}</a></li>')
    toc_items.append('</ul></li>')

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>7月外卖门店运营偏差通报（截至7月7日）</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #f5f6fa; color: #2c3e50; line-height: 1.7; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}

  /* Header */
  .header {{ background: linear-gradient(135deg, #2c3e50, #e74c3c); color: #fff; padding: 30px 40px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 24px; margin-bottom: 6px; }}
  .header .sub {{ font-size: 14px; opacity: .85; }}

  /* TOC */
  .toc {{ background: #fff; border-radius: 10px; padding: 20px 30px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
  .toc h3 {{ font-size: 16px; margin-bottom: 12px; color: #e74c3c; }}
  .toc ul {{ list-style: none; padding-left: 16px; }}
  .toc li {{ margin: 4px 0; }}
  .toc a {{ color: #2c3e50; text-decoration: none; font-size: 14px; }}
  .toc a:hover {{ color: #e74c3c; }}
  .toc-mkt {{ font-weight: bold; font-size: 15px; margin-top: 8px; }}
  .badge {{ font-size: 12px; background: #fadbd8; color: #c0392b; padding: 1px 8px; border-radius: 10px; margin-left: 4px; }}

  /* Charts */
  .chart-box {{ background: #fff; border-radius: 10px; padding: 20px 30px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
  .chart-box h3 {{ font-size: 16px; margin-bottom: 12px; color: #2c3e50; }}
  .chart-box img {{ max-width: 100%; border-radius: 8px; }}

  /* Sections */
  .section {{ background: #fff; border-radius: 10px; padding: 24px 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.06); border-left: 4px solid #e74c3c; }}
  .section h2 {{ font-size: 20px; color: #2c3e50; margin-bottom: 16px; }}

  /* Summary grid */
  .summary-grid {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }}
  .stat-card {{ background: #f8f9fa; border-radius: 8px; padding: 10px 18px; text-align: center; min-width: 80px; }}
  .stat-card .num {{ font-size: 22px; font-weight: bold; color: #2c3e50; }}
  .stat-card .label {{ font-size: 11px; color: #7f8c8d; }}
  .stat-card.alert {{ background: #fde8e8; }}
  .stat-card.alert .num {{ color: #e74c3c; }}

  /* Problem bar */
  .problem-bar {{ background: #fde8e8; border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; font-size: 13px; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0 16px; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8f9fa; font-weight: 600; color: #555; font-size: 12px; }}
  tr:hover {{ background: #fafafa; }}

  /* Tags */
  .red {{ color: #e74c3c; font-weight: 600; }}
  .zero {{ color: #bdc3c7; }}
  .dim-tag {{ display: inline-block; background: #fde8e8; color: #c0392b; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin: 2px 3px; }}
  .dim-tag.blue {{ background: #d6eaf8; color: #2980b9; }}
  h3 {{ font-size: 15px; margin: 16px 0 8px; color: #555; border-bottom: 2px solid #eee; padding-bottom: 4px; }}

  /* Footer */
  .footer {{ text-align: center; padding: 20px; color: #95a5a6; font-size: 12px; }}

  @media print {{
    body {{ background: #fff; }}
    .section {{ box-shadow: none; break-inside: avoid; }}
  }}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>7月外卖门店运营偏差通报</h1>
  <div class="sub">数据周期：2026年7月1日 — 7月7日 ｜ 覆盖门店：{len(store_map)}家 ｜ 预警总数：{len(alerts)}条</div>
  <div class="sub" style="font-size:12px;margin-top:4px">数据源：D:/工作/workbuddy/ ｜ 生成时间：2026-07-08</div>
</div>

<div class="toc">
  <h3>📑 目录</h3>
  <ul>{"".join(toc_items)}</ul>
</div>

<div class="chart-box">
  <h3>📊 各市场品牌问题概览</h3>
  <img src="chart_overview.png" alt="各市场品牌问题概览">
</div>

<div class="chart-box">
  <h3>📊 预警类型分布</h3>
  <img src="chart_alert_types.png" alt="预警类型分布">
</div>

<div class="chart-box">
  <h3>📊 各市场品牌核心病灶 TOP5</h3>
  <img src="chart_dim_problems.png" alt="核心病灶">
</div>

<div class="chart-box">
  <h3>📊 区经理问题密度排行</h3>
  <img src="chart_area_mgr.png" alt="区经理排行">
</div>

{"".join(sections_html)}

<div class="footer">
  本报告由看板系统自动生成 ｜ 数据截止 2026-07-07 ｜ 疑问请反馈运营部
</div>

</div>
</body>
</html>'''

# Write
html_path = os.path.join(OUT_DIR, 'index.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Done! Report: {html_path}')
print(f'Charts: {OUT_DIR}/chart_*.png')
print(f'Size: {os.path.getsize(html_path)} bytes')
