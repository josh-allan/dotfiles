
import Widget from "resource:///com/github/Aylur/ags/widget.js";
import Battery from "resource:///com/github/Aylur/ags/service/battery.js";

// Define a function to format the battery percentage
function formatPercentage(p) {
    return `${p.toFixed(0)}%`;
}

// Create a Label widget to display the battery percentage
const batteryIndicator = () => Widget.Label({
    label: Battery.bind("percent").transform(formatPercentage),
    visible: Battery.bind("available"),
    class_name: "battery-container"
});

export default batteryIndicator;

