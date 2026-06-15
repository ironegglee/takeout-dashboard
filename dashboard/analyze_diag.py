import json
from collections import Counter, defaultdict

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

store_names = set()
if 'mp_stores' in data:
    for s in data['mp_stores']:
        store_names.add(s['name'])
if 'mt_stores' in data:
    for s in data['mt_stores']:
        store_names.add(s['name'])

print(f'=== Total unique stores: {len(store_names)} ===')

mp_map = {s['name']: s for s in data.get('mp_stores', [])}
mt_map = {s['name']: s for s in data.get('mt_stores', [])}

issue_counter = Counter()
status_counter = Counter()
issue_detail = defaultdict(list)

for name in sorted(store_names):
    mp = mp_map.get(name)
    mt = mt_map.get(name)
    issues = []
    status = 'ok'

    if mp:
        mp_avg = mp['avg']
        mp_rate = mp['rate']
        mp_max = mp.get('max', 0)

        if mp_avg > 15:
            status = 'bad'
            issues.append('avg_bad_gt15')
            issue_detail['avg_bad_gt15'].append((name, mp_avg, mp_rate))
        elif mp_avg > 8:
            issues.append('avg_good_8_15')
            issue_detail['avg_good_8_15'].append((name, mp_avg, mp_rate))
        else:
            issue_detail['avg_excellent_le8'].append((name, mp_avg, mp_rate))

        if mp_rate < 70:
            status = 'bad'
            issues.append('rate_bad_lt70')
            issue_detail['rate_bad_lt70'].append((name, mp_avg, mp_rate))
        elif mp_rate < 85:
            if status == 'ok': status = 'warn'
            issues.append('rate_warn_70_85')
            issue_detail['rate_warn_70_85'].append((name, mp_avg, mp_rate))

        if mp_max > 15:
            issue_detail['max_gt15'].append((name, mp_max))

    if mt:
        shop_score = mt['shop_score']
        exp_score = mt['exp_score']
        sd = mt.get('shop_dims', {})
        ed = mt.get('exp_dims', {})

        if shop_score < 85:
            status = 'bad'
            issues.append('shop_bad_lt85')
            issue_detail['shop_bad_lt85'].append((name, shop_score, exp_score))
        elif shop_score < 95:
            if status == 'ok': status = 'warn'
            issues.append('shop_warn_85_95')
            issue_detail['shop_warn_85_95'].append((name, shop_score, exp_score))

        if exp_score < 4.0:
            status = 'bad'
            issues.append('exp_bad_lt4')
            issue_detail['exp_bad_lt4'].append((name, shop_score, exp_score))
        elif exp_score < 4.6:
            if status == 'ok': status = 'warn'
            issues.append('exp_warn_4_4.6')
            issue_detail['exp_warn_4_4.6'].append((name, shop_score, exp_score))

        shop_dims = [
            ('差评回复率', sd.get('reply_rate', 0)),
            ('商家评分', sd.get('merchant_rating', 0)),
            ('高峰营业', sd.get('peak_hours', 0)),
            ('不接单率', sd.get('reject_rate', 0)),
            ('基础营业', sd.get('base_hours', 0)),
            ('出餐上报', sd.get('cook_report', 0))
        ]
        worst_shop = min(shop_dims, key=lambda x: x[1])
        if worst_shop[1] < 95:
            issue_detail['shop_worst_dim'].append((name, worst_shop[0], worst_shop[1]))

        exp_dims = [
            ('商品满意度', ed.get('product_sat', 0)),
            ('包装满意度', ed.get('pack_sat', 0)),
            ('复购率', ed.get('repurchase', 0)),
            ('消息回复', ed.get('msg_reply', 0)),
            ('服务负反馈', ed.get('service_neg', 0)),
            ('食安负反馈', ed.get('food_safety', 0))
        ]
        worst_exp = min(exp_dims, key=lambda x: x[1])
        if worst_exp[1] < 4.6:
            issue_detail['exp_worst_dim'].append((name, worst_exp[0], worst_exp[1]))

    if not mp and not mt:
        status = 'warn'
        issues.append('no_data')
        issue_detail['no_data'].append(name)

    for i in issues:
        issue_counter[i] += 1
    status_counter[status] += 1
    issue_detail['_store_summary'].append({
        'name': name, 'status': status, 'issues': issues,
        'mp_avg': mp['avg'] if mp else None,
        'mp_rate': mp['rate'] if mp else None,
        'mt_shop': mt['shop_score'] if mt else None,
        'mt_exp': mt['exp_score'] if mt else None,
    })

print('\n=== STATUS DISTRIBUTION ===')
for k, v in sorted(status_counter.items()):
    print(f'  {k}: {v} stores')

print('\n=== ISSUE TYPE COUNTS ===')
for k, v in issue_counter.most_common():
    print(f'  {k}: {v}')

print('\n=== MP AVG DISTRIBUTION ===')
avgs = []
for s in data.get('mp_stores', []):
    avgs.append(s['avg'])
if avgs:
    import statistics
    print(f'  Stores: {len(avgs)}, Min: {min(avgs):.1f}, Max: {max(avgs):.1f}, Mean: {statistics.mean(avgs):.1f}')
    print(f'  <=8: {sum(1 for a in avgs if a <= 8)}, 8-15: {sum(1 for a in avgs if 8 < a <= 15)}, >15: {sum(1 for a in avgs if a > 15)}')

print('\n=== MP RATE DISTRIBUTION ===')
rates = []
for s in data.get('mp_stores', []):
    rates.append(s['rate'])
if rates:
    import statistics
    print(f'  Stores: {len(rates)}, Min: {min(rates):.1f}, Max: {max(rates):.1f}, Mean: {statistics.mean(rates):.1f}')
    print(f'  <70: {sum(1 for r in rates if r < 70)}, 70-85: {sum(1 for r in rates if 70 <= r < 85)}, >=85: {sum(1 for r in rates if r >= 85)}')

print('\n=== MT SHOP SCORE DISTRIBUTION ===')
shops = []
for s in data.get('mt_stores', []):
    shops.append(s['shop_score'])
if shops:
    import statistics
    print(f'  Stores: {len(shops)}, Min: {min(shops):.1f}, Max: {max(shops):.1f}, Mean: {statistics.mean(shops):.1f}')
    print(f'  <85: {sum(1 for s in shops if s < 85)}, 85-95: {sum(1 for s in shops if 85 <= s < 95)}, >=95: {sum(1 for s in shops if s >= 95)}')

print('\n=== MT EXP SCORE DISTRIBUTION ===')
exps = []
for s in data.get('mt_stores', []):
    exps.append(s['exp_score'])
if exps:
    import statistics
    print(f'  Stores: {len(exps)}, Min: {min(exps):.2f}, Max: {max(exps):.2f}, Mean: {statistics.mean(exps):.2f}')
    print(f'  <4.0: {sum(1 for e in exps if e < 4.0)}, 4.0-4.6: {sum(1 for e in exps if 4.0 <= e < 4.6)}, >=4.6: {sum(1 for e in exps if e >= 4.6)}')

print('\n=== WORST SHOP DIM (score<95) ===')
shop_worst = Counter()
for _, dim, val in issue_detail.get('shop_worst_dim', []):
    shop_worst[dim] += 1
for k, v in shop_worst.most_common():
    print(f'  {k}: {v} stores')

print('\n=== WORST EXP DIM (score<4.6) ===')
exp_worst = Counter()
for _, dim, val in issue_detail.get('exp_worst_dim', []):
    exp_worst[dim] += 1
for k, v in exp_worst.most_common():
    print(f'  {k}: {v} stores')

print('\n=== BAD/WARN STORE DETAILS ===')
for s in issue_detail.get('_store_summary', []):
    if s['status'] in ('bad', 'warn'):
        print(f'  [{s["status"].upper():4s}] mp_avg={s["mp_avg"]}, mp_rate={s["mp_rate"]}, mt_shop={s["mt_shop"]}, mt_exp={s["mt_exp"]}  |  {s["name"]}')

print('\n=== COMPLETE - ALL COMBINATIONS ===')
combo = Counter()
for s in issue_detail.get('_store_summary', []):
    combo[tuple(sorted(s['issues']))] += 1
for k, v in combo.most_common():
    labels = [x.replace('avg_bad_gt15','出餐>15min').replace('avg_good_8_15','出餐8-15min')
              .replace('avg_excellent_le8','出餐≤8min').replace('rate_bad_lt70','达标率<70%')
              .replace('rate_warn_70_85','达标率70-85%').replace('shop_bad_lt85','店铺分<85')
              .replace('shop_warn_85_95','店铺分85-95').replace('exp_bad_lt4','体验分<4.0')
              .replace('exp_warn_4_4.6','体验分4.0-4.6').replace('no_data','无数据') for x in k]
    print(f'  {v} stores: [{", ".join(labels)}]')
