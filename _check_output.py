import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/CYYS/WorkBuddy/2026-06-16-11-25-31/dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('mt_stores:', len(d.get('mt_stores', [])))
print('mp_stores:', len(d.get('mp_stores', [])))
print('alerts:', len(d.get('alerts', [])))
print('date_range:', d.get('full_date_range'))

# Check match_summary
ms = d.get('match_summary', {})
print('match_summary:', ms)
