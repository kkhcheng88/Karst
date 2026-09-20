/* Only explicit public chart projections are loaded. No market/API credentials. */
document.querySelectorAll('[data-chart]').forEach(async root => {
  const status=root.querySelector('.chart-status'), canvas=root.querySelector('.chart-canvas');
  try {
    if(!window.LightweightCharts) throw new Error('Chart library unavailable');
    const response=await fetch(root.dataset.chart);
    if(!response.ok) throw new Error('Chart data unavailable');
    const data=await response.json(), L=window.LightweightCharts;
    canvas.hidden=false;
    const chart=L.createChart(canvas,{autoSize:true,layout:{textColor:'#344b41',background:{type:'solid',color:'#ffffff'},attributionLogo:true},
      grid:{vertLines:{color:'#f2f4f0'},horzLines:{color:'#e9eee8'}},rightPriceScale:{borderColor:'#dce1d8'},
      timeScale:{borderColor:'#dce1d8',timeVisible:false},localization:{locale:'zh-TW'}});
    const candle=chart.addSeries(L.CandlestickSeries,{upColor:'#25866a',downColor:'#bb625b',borderVisible:false,wickUpColor:'#25866a',wickDownColor:'#bb625b'});
    const volume=chart.addSeries(L.HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:'volume'},1);
    chart.panes()[0].setStretchFactor(4);chart.panes()[1].setStretchFactor(1);
    const colors=['#8a67aa','#587da1','#ae813b'];
    let overlays=[],levels=[],view;
    const applyOptions=()=>{
      overlays.forEach(s=>s.applyOptions({visible:root.querySelector('[data-ma]').checked}));
      levels.forEach(l=>l.applyOptions({lineVisible:root.querySelector('[data-levels]').checked,axisLabelVisible:root.querySelector('[data-levels]').checked}));
    };
    const show=()=>{
      view=data.views[root.querySelector('[data-period]').value];
      overlays.forEach(s=>chart.removeSeries(s)); levels.forEach(l=>candle.removePriceLine(l));
      candle.setData(view.bars.map(({time,open,high,low,close})=>({time,open,high,low,close})));
      volume.setData(view.bars.map(b=>({time:b.time,value:b.volume,color:b.close>=b.open?'#72b29e':'#d69993'})));
      overlays=view.lines.map((line,i)=>{const s=chart.addSeries(L.LineSeries,{color:colors[i%colors.length],lineWidth:1,title:line.name,lastValueVisible:false,priceLineVisible:false});s.setData(line.data);return s;});
      levels=view.levels.map(l=>candle.createPriceLine({price:l.price,title:l.label,color:l.kind==='support'?'#287962':l.kind==='resistance'?'#a45349':'#87938a',lineWidth:1,lineStyle:2,axisLabelVisible:true}));
      const n=view.bars.length;chart.timeScale().setVisibleLogicalRange({from:Math.max(0,n-100),to:n+4});
      const last=view.bars[n-1];
      status.textContent=`${data.currency} · ${data.price_basis} · 截至 ${data.as_of} · ${last.complete?'最後一根已收線':'最後一根未收線'}`;
      root.querySelector('.chart-reading').textContent=`${last.time}  收 ${last.close.toFixed(2)}`;
      applyOptions();
    };
    chart.subscribeCrosshairMove(param=>{
      const b=param.seriesData.get(candle);if(!b)return;
      const t=typeof b.time==='string'?b.time:`${b.time.year}-${b.time.month}-${b.time.day}`;
      root.querySelector('.chart-reading').textContent=`${t}  開 ${b.open.toFixed(2)}  高 ${b.high.toFixed(2)}  低 ${b.low.toFixed(2)}  收 ${b.close.toFixed(2)}`;
    });
    root.querySelector('[data-period]').addEventListener('change',show);
    root.querySelector('[data-ma]').addEventListener('change',applyOptions);
    root.querySelector('[data-levels]').addEventListener('change',applyOptions);
    root.querySelector('[data-fit]').addEventListener('click',()=>chart.timeScale().fitContent());
    root.querySelector('.chart-tools').hidden=false;show();
    root.dataset.loaded='true';
    const fallback=root.nextElementSibling;if(fallback?.classList.contains('static-chart'))fallback.open=false;
  }catch(error){canvas.hidden=true;status.textContent='互動圖暫未載入，請查看下方靜態圖。';root.dataset.loaded='false';}
});
