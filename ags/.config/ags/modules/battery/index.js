import Widget from "resource:///com/github/Aylur/ags/widget.js";
import Battery from "resource:///com/github/Aylur/ags/service/battery.js";

const batteryProgress = Widget.CircularProgress({
  child: Widget.Icon({
    icon: Battery.bind("icon-name"),
  }),
  visible: Battery.bind("available"),
  value: Battery.bind("percent").transform((p) => (p > 0 ? p / 100 : 0)),
  class_name: Battery.bind("charging").transform((ch) =>
    ch ? "charging" : "",
  ),
});

export default batteryProgress;
