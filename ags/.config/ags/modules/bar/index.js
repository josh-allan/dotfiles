import { Variable } from 'resource:///com/github/Aylur/ags/variable.js';
import Widget from 'resource:///com/github/Aylur/ags/widget.js';
import Workspaces from "../workspaces/index.js";
import FocusedTitle from "../title/index.js";
import RoundedCorner, {RoundedAngleEnd} from "../roundedCorner/index.js";
import Tray from "../systemtray/index.js";
import Clock from "../clock/index.js"
import Indicator from '../indicator/index.js'
import Audio from 'resource:///com/github/Aylur/ags/service/audio.js'
import Brightness from '../brightness/index.js'
import App from 'resource:///com/github/Aylur/ags/app.js'
import { timeout } from 'resource:///com/github/Aylur/ags/utils.js'
import { NotificationIndicator } from '../notifications/index.js'
import { MusicBarContainer } from '../mpris/index.js';

const time = new Variable('', {
    poll: [1000, 'date'],
})

const Right = () => Widget.EventBox({
    hpack: 'end',
    child: Widget.Box({
        children: [
            RoundedAngleEnd("topleft", {class_name: "corner", hexpand: true}),
            Tray(),
            Widget.EventBox({
                on_primary_click_release: () => App.openWindow("sideright"),
                on_secondary_click_release: () => App.openWindow("launcher"),
                on_scroll_up: (box, evt) => {
                    if (Audio.speaker == null) return;
                    Audio.speaker.volume += 0.03;
                    Indicator.popup(1);
                },
                on_scroll_down: () => {
                    if (Audio.speaker == null) return;
                    Audio.speaker.volume -= 0.03;
                    Indicator.popup(1);
                },
                child: Widget.Box({
                    children: [
                        NotificationIndicator(),
                        Clock(),
                    ]
                })
            })
        ]
    })
})

const Center = () => Widget.Box({
    children: [
        MusicBarContainer()
    ]
})

const Left = () => Widget.EventBox({
    on_scroll_up: (box, evt) => {
        Brightness.screen_value += 0.03
        Indicator.popup(1);
    },
    on_scroll_down: () => {
        Brightness.screen_value -= 0.03;
        Indicator.popup(1);
    },
    child: Widget.Box({
        children:[
            Workspaces(),
            FocusedTitle(),
            RoundedAngleEnd("topright", {class_name: "angle"})
        ]
    }),
})

const Bar = () => Widget.CenterBox({
  start_widget: Left(),
  center_widget: Center(),
  end_widget: Right(),
})

const BarRevealer = (windowName) => Widget.Box({
  class_name: 'bar-revealer',
  children:[
    Widget.Revealer({
      setup: (rev) => timeout(10, () => rev.reveal_child = true),
      transition: 'slide_down',
      reveal_child: false,
      child: Bar(),
      transitionDuration: 350,
      connections: [[App, (revealer, name, visible) => {
        if (name === windowName)
          revealer.reveal_child = visible;
      }]],
    })
  ]  
})

const BarWindow = (/** @type {number} */ monitor) => Widget.Window({
    monitor,
    name: `bar${monitor}`,
    anchor: ['top', 'left', 'right'],
    exclusivity: 'exclusive',
    child: BarRevealer(`bar${monitor}`)
})

export default BarWindow;
