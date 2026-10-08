from pathlib import Path
import copy, csv, json, shutil, uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dashboard_complete'

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2), encoding='utf-8')
def literal(v): return {'expr': {'Literal': {'Value': v}}}
def text_value(v): return literal("'" + v + "'")
def color(v): return {'solid': {'color': text_value(v)}}
def field(table, name, measure=False):
    return {('Measure' if measure else 'Column'): {
        'Expression': {'SourceRef': {'Entity': table}}, 'Property': name}}
def projection(table, name, measure=False, label=None):
    return {'field': field(table, name, measure), 'queryRef': table+'.'+name,
            'nativeQueryRef': label or name, 'displayName': label or name}

# Create a separate project; never overwrite the original.
projects = [p for p in ROOT.rglob('*.pbip') if not any(
    part in {'.venv', 'dashboard_complete', 'dashboard_professional'}
    for part in p.relative_to(ROOT).parts)]
if len(projects) != 1:
    raise RuntimeError('Keep exactly one original PBIP project under airline-pricing-analysis.')
if OUT.exists():
    raise RuntimeError('Rename the existing dashboard_complete folder before running again.')
source = projects[0]
for filename in ['current_vs_history.csv', 'booking_curves.csv', 'pricing_scenarios.csv']:
    if not (ROOT/'data'/filename).exists(): raise FileNotFoundError(filename)
OUT.mkdir()
shutil.copy2(source, OUT/source.name)
for suffix in ['.Report', '.SemanticModel']:
    folder = source.parent/(source.stem+suffix)
    shutil.copytree(folder, OUT/folder.name, ignore=shutil.ignore_patterns('.pbi'))
report = OUT/(source.stem+'.Report')
model = OUT/(source.stem+'.SemanticModel')
pages = report/'definition/pages'
meta = read(pages/'pages.json')
original = pages/meta['pageOrder'][0]
page_template = read(original/'page.json')
visuals = [read(p) for p in (original/'visuals').glob('*/visual.json')]
SCHEMA = visuals[0]['$schema']
cards = {v['visual']['query']['queryState']['Data']['projections'][0]
         ['field']['Measure']['Property']: v for v in visuals
         if v['visual']['visualType'] == 'cardVisual'}

# Text-based model tables use the existing local CSV files.
def add_table(name, integer_columns, boolean_columns, date_columns):
    with (ROOT/'data'/(name+'.csv')).open(encoding='utf-8-sig') as handle:
        columns = next(csv.reader(handle))
    parts = ['table '+name]
    types = []
    for col in columns:
        if col in date_columns: dtype, mtype = 'dateTime', 'type date'
        elif col in boolean_columns: dtype, mtype = 'boolean', 'type logical'
        elif col in integer_columns: dtype, mtype = 'int64', 'Int64.Type'
        elif col in ['flight_id', 'route']: dtype, mtype = 'string', 'type text'
        else: dtype, mtype = 'double', 'type number'
        parts += [f'\tcolumn {col}', f'\t\tdataType: {dtype}',
                  '\t\tsummarizeBy: none', f'\t\tsourceColumn: {col}']
        if dtype == 'double': parts += ['\t\tformatString: 0.00']
        types.append('{"'+col+'", '+mtype+'}')
    if name == 'booking_curves':
        measures = {
            'Selected Flight LF (%)': 'IF(HASONEVALUE(current_vs_history[flight_id]), AVERAGE(booking_curves[load_factor_pct]))',
            'Historical LF (%)': 'IF(HASONEVALUE(current_vs_history[flight_id]), AVERAGE(booking_curves[historical_load_factor_pct]))'}
    else:
        measures = {
            'Future Revenue EUR': 'IF(HASONEVALUE(current_vs_history[flight_id]), SUM(pricing_scenarios[future_sales_revenue_eur]))',
            'Revenue Change EUR': 'IF(HASONEVALUE(current_vs_history[flight_id]), SUM(pricing_scenarios[revenue_change_eur]))'}
    for label, dax in measures.items():
        parts += [f"\tmeasure '{label}' = {dax}", '\t\tformatString: #,0.00']
    csvpath = str(ROOT/'data'/(name+'.csv'))
    # Explicit locale makes decimal-point CSV parsing independent of Windows settings.
    parts += [f'\tpartition {name} = m', '\t\tmode: import', '\t\tsource =',
              '\t\t\tlet',
              f'\t\t\t\tSource = Csv.Document(File.Contents("{csvpath}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
              '\t\t\t\tHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
              '\t\t\t\tTyped = Table.TransformColumnTypes(Headers, {'+', '.join(types)+'}, "en-US")',
              '\t\t\tin Typed']
    (model/'definition/tables'/(name+'.tmdl')).write_text('\n'.join(parts)+'\n', encoding='utf-8')
    rel=model/'definition/relationships.tmdl'
    with rel.open('a', encoding='utf-8') as handle:
        handle.write(f'\nrelationship {uuid.uuid4()}\n\tfromColumn: {name}.flight_id\n\ttoColumn: current_vs_history.flight_id\n')
    model_file=model/'definition/model.tmdl'
    with model_file.open('a',encoding='utf-8') as handle:
        handle.write(f'\nref table {name}\n')

add_table('booking_curves', {'days_before_departure','booked_passengers','historical_peer_count'}, {'is_synthetic'}, {'departure_date','checkpoint_date'})
add_table('pricing_scenarios', {'days_to_departure','seats_remaining'}, {'is_synthetic','capacity_constrained'}, set())

# Preserve original measures and add a weighted route comparison.
table_file=model/'definition/tables/current_vs_history.tmdl'
content=table_file.read_text(encoding='utf-8-sig')
content=content.replace('\n\tcolumn flight_id',
    "\n\tmeasure 'Weighted Gap (pp)' = DIVIDE(SUMX(current_vs_history, current_vs_history[capacity] * current_vs_history[gap_same_lead_pp]), SUM(current_vs_history[capacity]))\n\t\tformatString: 0.00\n\n\tcolumn flight_id",1)
for col in ['load_factor_now_pct','benchmark_same_lead_pct','gap_same_lead_pp','average_fare_now_eur']:
    start=content.index('\tcolumn '+col+'\n'); end=content.find('\n\tcolumn ',start+1)
    if end<0:end=content.index('\n\tpartition ',start)
    block=content[start:end].replace('summarizeBy: sum','summarizeBy: none')
    block=block.replace('dataType: double','dataType: double\n\t\tformatString: 0.00')
    content=content[:start]+block+content[end:]
table_file.write_text(content,encoding='utf-8')

# Native Power BI visuals; fixed canvas, consistent typography and spacing.
def visual(name, kind, roles=None):
    v={'$schema':SCHEMA,'name':name,'position':{},'visual':{'visualType':kind,'drillFilterOtherVisuals':True}}
    if roles:v['visual']['query']={'queryState':{role:{'projections':items} for role,items in roles.items()}}
    return v

def place(page,v,x,y,w,h,title=None):
    v=copy.deepcopy(v)
    v['position']={'x':x,'y':y,'width':w,'height':h,'z':10,'tabOrder':10}
    objects={'background':[{'properties':{'show':literal('true'),'color':color('#FFFFFF'),'transparency':literal('0D')}}],
             'border':[{'properties':{'show':literal('true'),'color':color('#DCE5ED'),'radius':literal('10D')}}]}
    if title:objects['title']=[{'properties':{'show':literal('true'),'text':text_value(title),'fontColor':color('#142D46'),'fontSize':literal('12D')}}]
    v['visual']['visualContainerObjects']=objects
    write(page/'visuals'/v['name']/'visual.json',v)

def textbox(page,name,lines,x,y,w,h,size=16,background='#FFFFFF',font='#142D46'):
    v=visual(name,'textbox')
    v['visual']['objects']={'general':[{'properties':{'paragraphs':[
        {'textRuns':[{'value':line,'textStyle':{'fontFamily':'Segoe UI','fontSize':f'{size}pt','color':font}}]} for line in lines]}}]}
    place(page,v,x,y,w,h)
    p=page/'visuals'/name/'visual.json';v=read(p)
    v['visual']['visualContainerObjects']['background'][0]['properties']['color']=color(background)
    write(p,v)

def new_page(name,label,title):
    p=pages/name; d=copy.deepcopy(page_template)
    d.update(name=name,displayName=label,width=1440,height=900)
    d['objects']={'background':[{'properties':{'color':color('#F2F5F8'),'transparency':literal('0D')}}]}
    write(p/'page.json',d)
    textbox(p,'header',[title],24,20,1392,76,25,'#142D46','#FFFFFF')
    return p

def slicer(page,name,column,x,y,w,h,label,single=False):
    v=visual(name,'slicer',{'Values':[projection('current_vs_history',column)]})
    v['visual']['objects']={'data':[{'properties':{'mode':text_value('Dropdown')}}],
        'selection':[{'properties':{'singleSelect':literal('true' if single else 'false')}}]}
    place(page,v,x,y,w,h,label)

p=new_page('overview','01 | Portfolio Overview','FORWARD BOOKING OVERVIEW')
textbox(p,'date',['Portfolio snapshot | 7 October 2026 | Currency: EUR'],24,100,1392,38,12,'#F2F5F8')
for i,name in enumerate(['Flights Count','Seats Remaining','Booked Revenue EUR','Booked Load Factor']):
    place(p,cards[name],24+i*350,150,342,140)
slicer(p,'route_filter','route',24,310,240,190,'Route')
v=visual('route_comparison','clusteredBarChart',{'Category':[projection('current_vs_history','route')],
    'Y':[projection('current_vs_history','Weighted Gap (pp)',True)]})
v['visual']['objects']={'dataPoint':[{'properties':{'fill':color('#087F8C')}}]}
place(p,v,284,310,1132,220,'Capacity-weighted booking gap vs history (pp)')
columns=['flight_id','days_to_departure','load_factor_now_pct','benchmark_same_lead_pct','gap_same_lead_pp','seats_remaining','bookings_last_7_days']
labels=['Flight','Days to departure','Booked LF (%)','Historical LF (%)','Gap (pp)','Seats remaining','7-day bookings']
v=visual('flight_table','tableEx',{'Values':[projection('current_vs_history',c,label=l) for c,l in zip(columns,labels)]})
v['visual']['query']['sortDefinition']={'sort':[{'field':field('current_vs_history','gap_same_lead_pp'),'direction':'Ascending'}]}
v['visual']['objects']={'total':[{'properties':{'totals':literal('false')}}]}
place(p,v,24,550,1392,322,'Upcoming flights | weakest booking pace first')

p=new_page('pace','02 | Booking Pace','BOOKING PACE & HISTORICAL BENCHMARK')
slicer(p,'flight_filter','flight_id',24,120,360,100,'Select ONE flight',True)
textbox(p,'pace_hint',['Select one flight to display its curve. Only elapsed checkpoints are included.'],410,120,1006,80,14,'#F2F5F8')
v=visual('booking_curve','lineChart',{'Category':[projection('booking_curves','days_before_departure')],
    'Y':[projection('booking_curves','Selected Flight LF (%)',True),projection('booking_curves','Historical LF (%)',True)]})
v['visual']['query']['sortDefinition']={'sort':[{'field':field('booking_curves','days_before_departure'),'direction':'Descending'}]}
place(p,v,24,245,1392,455,'Cumulative booked load factor (%) | days before departure, 60 → 0')
v=visual('checkpoint_table','tableEx',{'Values':[projection('booking_curves',c) for c in ['flight_id','days_before_departure','booked_passengers','load_factor_pct','historical_load_factor_pct','gap_pp']]})
v['visual']['objects']={'total':[{'properties':{'totals':literal('false')}}]}
place(p,v,24,720,1392,155,'Checkpoint detail')

p=new_page('scenarios','03 | Pricing Scenarios','PRICING SCENARIOS & REVENUE SENSITIVITY')
slicer(p,'scenario_flight','flight_id',24,120,360,100,'Select ONE flight',True)
textbox(p,'scenario_hint',['Independent price and demand assumptions. These are scenarios, not demand predictions.'],410,120,1006,80,14,'#F2F5F8')
for i,(measure,label) in enumerate([('Future Revenue EUR','Future ticket revenue (EUR)'),('Revenue Change EUR','Change vs baseline (EUR)')]):
    v=visual('matrix_'+str(i),'pivotTable',{'Rows':[projection('pricing_scenarios','demand_change_pct')],
        'Columns':[projection('pricing_scenarios','price_change_pct')],
        'Values':[projection('pricing_scenarios',measure,True)]})
    v['visual']['objects']={'subTotals':[{'properties':{'rowSubtotals':literal('false'),'columnSubtotals':literal('false')}}]}
    place(p,v,24+i*704,250,688,350,label+' | rows: demand %, columns: price %')
textbox(p,'scenario_note',['Baseline: historical remaining booking pickup at the same lead time.',
    'Future fare assumption: route base fare × 1.45. Existing bookings are unchanged.',
    'Additional sales are capped at remaining seat capacity; fractional passengers are expected values.',
    'Do not add scenarios together or interpret them as an optimal-price recommendation.'],24,625,1392,220,17)

p=new_page('method','04 | Methodology','METHODOLOGY & DECISION LIMITS')
textbox(p,'method_notes',['Entirely synthetic portfolio case study; not Icelandair data.',
    'Analysis date: end of 7 October 2026. All monetary values are EUR.',
    'Three illustrative routes, 54 future flights, 33 historical peers per route.',
    '', 'Historical benchmarks match route and days before departure.',
    'Zero-booking flights remain in the benchmark. Future checkpoints are excluded.',
    'Portfolio gap is weighted by capacity; it is descriptive, not statistical significance.',
    '', 'No cancellations, group bookings, overbooking, connections or fare restrictions.',
    'Seasonality, weekday patterns and competitor offers are not controlled for.',
    'Booked revenue is cumulative ticket sales, not recognized revenue or profit.',
    '', 'Generator demand levels and late-booking fare patterns are assumptions.',
    'Scenarios do not estimate causal price elasticity or identify an optimal fare.',
    'Operational pricing decisions would require further commercial evidence.'],24,125,1392,745,18)
for old in list(pages.iterdir()):
    if old.is_dir() and old.name not in {'overview','pace','scenarios','method'}:shutil.rmtree(old)
meta.update(pageOrder=['overview','pace','scenarios','method'],activePageName='overview')
write(pages/'pages.json',meta)
for path in OUT.rglob('*.json'):read(path)
print('Created:',OUT/source.name)
print('Open the new project in Power BI, Refresh, then select ONE flight on pages 2 and 3.')
print('Native visual rendering still needs verification in Power BI Desktop.')
