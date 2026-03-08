---
name: d3js-visualization
description: "D3.js визуализации: интерактивные графики, диаграммы, сети, карты. Используй когда нужна кастомная SVG-визуализация данных с анимациями, tooltips, zoom — то что стандартные chart-библиотеки не могут."
allowed-tools: Bash,Write,Read,Edit
---

# D3.js Visualization — Интерактивные визуализации данных

Создание кастомных интерактивных визуализаций с полным контролем над SVG-элементами, переходами и взаимодействием.

> Источник: https://github.com/chrisvoncsefalvay/claude-d3js-skill

## Когда использовать

- Кастомные графики, которых нет в Chart.js / Recharts
- Force-directed network графы (связи между элементами)
- Географические визуализации (карты с данными)
- Chord диаграммы, Sankey, treemap
- Нужен полный контроль: анимации, zoom, drag, brush
- Interactive dashboards с нестандартным UX

## Когда НЕ использовать

- Простой bar/line/pie chart → используй Chart.js или Recharts
- Dashboard с типовыми виджетами → используй `dashboard-builder`
- Статичная инфографика → используй `canvas-design`
- Excel/таблицы → используй `excel-generation`

## Паттерны интеграции

### Pattern A: Direct DOM (Vanilla JS)
```javascript
const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width)
  .attr('height', height);
```

### Pattern B: React Integration
```tsx
import { useRef, useEffect } from 'react';
import * as d3 from 'd3';

function Chart({ data }) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.length) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // cleanup
    // ... D3 код
  }, [data]);

  return <svg ref={svgRef} />;
}
```

## Типы визуализаций

### Bar Chart
```javascript
svg.selectAll('rect')
  .data(data)
  .join('rect')
  .attr('x', d => xScale(d.label))
  .attr('y', d => yScale(d.value))
  .attr('width', xScale.bandwidth())
  .attr('height', d => height - yScale(d.value))
  .attr('fill', '#4f46e5');
```

### Line Chart
```javascript
const line = d3.line()
  .x(d => xScale(d.date))
  .y(d => yScale(d.value))
  .curve(d3.curveMonotoneX);

svg.append('path')
  .datum(data)
  .attr('d', line)
  .attr('fill', 'none')
  .attr('stroke', '#4f46e5')
  .attr('stroke-width', 2);
```

### Force-Directed Network
```javascript
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d => d.id))
  .force('charge', d3.forceManyBody().strength(-300))
  .force('center', d3.forceCenter(width / 2, height / 2));
```

### Pie / Donut Chart
```javascript
const pie = d3.pie().value(d => d.value);
const arc = d3.arc().innerRadius(50).outerRadius(100);

svg.selectAll('path')
  .data(pie(data))
  .join('path')
  .attr('d', arc)
  .attr('fill', (d, i) => colorScale(i));
```

## Интерактивность

### Tooltips
```javascript
const tooltip = d3.select('body').append('div')
  .attr('class', 'tooltip')
  .style('opacity', 0);

selection
  .on('mouseover', (event, d) => {
    tooltip.transition().duration(200).style('opacity', .9);
    tooltip.html(`Value: ${d.value}`)
      .style('left', `${event.pageX + 10}px`)
      .style('top', `${event.pageY - 28}px`);
  })
  .on('mouseout', () => {
    tooltip.transition().duration(500).style('opacity', 0);
  });
```

### Zoom & Pan
```javascript
const zoom = d3.zoom()
  .scaleExtent([0.5, 5])
  .on('zoom', (event) => {
    g.attr('transform', event.transform);
  });

svg.call(zoom);
```

### Transitions
```javascript
selection.transition()
  .duration(750)
  .ease(d3.easeCubicInOut)
  .attr('y', d => yScale(d.value))
  .attr('height', d => height - yScale(d.value));
```

## Scales Reference

| Scale | Использование | Пример |
|-------|--------------|--------|
| `scaleLinear` | Числовые данные | Оси Y/X |
| `scaleBand` | Категории | Бар-чарт |
| `scaleTime` | Даты | Таймлайн |
| `scaleOrdinal` | Цвета категорий | Легенда |
| `scaleSequential` | Heatmap | Тепловая карта |

## Responsive Design

```javascript
function resize() {
  const { width, height } = container.getBoundingClientRect();
  svg.attr('viewBox', `0 0 ${width} ${height}`);
  // Пересчёт scales и перерисовка
}

window.addEventListener('resize', resize);
```

## Performance

- **> 1000 элементов**: используй Canvas вместо SVG
- **Collision detection**: `d3.quadtree()` для spatial queries
- **Большие datasets**: виртуализация, progressive rendering
- **Анимации**: `requestAnimationFrame`, не `setInterval`

## Тёмная тема

```javascript
const darkColors = {
  background: '#1a1a2e',
  text: '#e0e0e0',
  grid: '#2a2a3e',
  primary: '#4f46e5',
  accent: '#f59e0b',
};
```
