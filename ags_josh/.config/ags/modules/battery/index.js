import Widget from "resource:///com/github/Aylur/ags/widget.js";
import Battery from "resource:///com/github/Aylur/ags/service/battery.js";

const batteryIndicator = Widget.CircularProgress({
  child: Widget.Icon({
    icon: Battery.bind("icon-name"),
  }),
  visible: Battery.bind("available"),
  value: Battery.bind("percent").transform((p) => (p > 0 ? p / 100 : 0)),
  class_name: Battery.bind("charging").transform((ch) =>
    ch ? "charging" : "",
  ),
});

// const batteryIndicator = Widget.ProgressBar({
//   value: Battery.bind("percent").as((p) => p / 100),
// });
export default batteryIndicator;
