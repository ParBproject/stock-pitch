import * as echarts from "echarts/core";
import { LineChart, BarChart, HeatmapChart, ScatterChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, DataZoomComponent, BrushComponent, ToolboxComponent,
  LegendComponent, VisualMapComponent, MarkLineComponent, MarkPointComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, BarChart, HeatmapChart, ScatterChart, GridComponent, TooltipComponent, DataZoomComponent, BrushComponent,
  ToolboxComponent, LegendComponent, VisualMapComponent, MarkLineComponent, MarkPointComponent, CanvasRenderer]);
export default echarts;
