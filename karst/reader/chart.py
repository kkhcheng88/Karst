"""Optional offline public chart renderer. Requires matplotlib; not used by Pages CI.

Render one explicitly selected registered daily price snapshot. Selection of the
source and judgment of support/resistance belong to the research agent.
"""
import argparse
from datetime import date
import json
from pathlib import Path


def render(source, config, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    rows = source['response']
    cutoff = date.fromisoformat(config['as_of'])
    rows = sorted((r for r in rows if date.fromisoformat(r['timestamp'][:10]) <= cutoff), key=lambda r: r['timestamp'])
    if not rows or rows[-1]['timestamp'][:10] != config['as_of']:
        raise ValueError('Selected snapshot does not reach the declared market close')
    if len({r['timestamp'][:10] for r in rows}) != len(rows):
        raise ValueError('Duplicate sessions in selected snapshot')
    closes = [float(r['close']) for r in rows]
    if abs(closes[-1] - config['expected_close']) > 0.005:
        raise ValueError('Chart and report close disagree')
    periods = config.get('moving_averages', [50, 200])
    if len(rows) < max(periods):
        raise ValueError('Insufficient history for the requested moving averages')
    count = min(config.get('sessions', 126), len(rows))
    start = len(rows) - count
    display = rows[start:]
    averages = {p: [sum(closes[i-p+1:i+1])/p if i+1 >= p else float('nan') for i in range(len(rows))][start:] for p in periods}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig, (ax, vol) = plt.subplots(2, 1, figsize=(13, 7.2), sharex=True, gridspec_kw={'height_ratios':[4,1]}, facecolor='white')
    for axis in (ax, vol):
        axis.set_facecolor('white')
        axis.grid(axis='y', color='#e6e9e3', lw=.7, zorder=0)
        axis.tick_params(colors='#53675d', labelsize=10)
        axis.spines['left'].set_color('#dce1d8')
        axis.spines['bottom'].set_color('#dce1d8')
    for i, r in enumerate(display):
        o,h,l,c = (float(r[k]) for k in ('open','high','low','close'))
        if not l <= min(o,c) <= max(o,c) <= h:
            raise ValueError('Invalid OHLC bar')
        color = '#248368' if c >= o else '#bc6460'
        ax.vlines(i,l,h,color=color,lw=.8,zorder=3)
        ax.add_patch(Rectangle((i-.32,min(o,c)),.64,max(abs(c-o),.12),facecolor=color,edgecolor=color,lw=.5,zorder=3))
        vol.bar(i,float(r['volume'])/1e6,color=color,width=.68,alpha=.75)
    colors = ['#758ca7','#b39a62','#8b7fab']
    for (p, series), color in zip(averages.items(), colors):
        ax.plot(range(count),series,color=color,lw=1.7,label=f'SMA {p}: ${series[-1]:.2f}',zorder=2)
    for level in config.get('zones', []):
        ax.axhspan(level['low'],level['high'],facecolor=level['color'],alpha=.13,zorder=1)
        ax.text(count+1,(level['low']+level['high'])/2,level['label'],va='center',fontsize=10,color=level['color'],clip_on=False)
    for level in config.get('lines', []):
        ax.axhline(level['price'],color=level['color'],lw=.9,ls='--',alpha=.7)
        ax.text(count+1,level['price'],level['label'],va='center',fontsize=10,color=level['color'],clip_on=False)
    ax.set_title(f"{config['title']}  |  Daily  |  Close ${closes[-1]:.2f}",loc='left',fontsize=17,fontweight='bold',pad=22,color='#233830')
    ax.set_ylabel('Price / USD',color='#53675d')
    ax.set_xlim(-1,count)
    ax.legend(loc='upper left',frameon=False,fontsize=10)
    vol.set_ylabel('Volume / M',color='#53675d')
    ticks = list(range(0,count,max(1,count//6)))
    vol.set_xticks(ticks,[display[i]['timestamp'][:10][5:] for i in ticks])
    fig.text(.08,.035,f"Through {config['as_of']}  |  {config['source_label']}  |  Support and resistance: analyst judgment",fontsize=9,color='#53675d')
    fig.subplots_adjust(left=.08,right=.80,top=.90,bottom=.115,hspace=.07)
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=150,facecolor='white',metadata={'Software':'Karst'})
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    render(json.loads(a.source.read_text()),json.loads(a.config.read_text()),a.output)


if __name__ == '__main__':
    main()
