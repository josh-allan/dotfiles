import Widget from 'resource:///com/github/Aylur/ags/widget.js'
import RoundedCorner, { RoundedAngleEnd } from "../roundedCorner/index.js";
import Mpris from 'resource:///com/github/Aylur/ags/service/mpris.js'
import icons from '../icons/index.js'
import GdkPixbuf from 'gi://GdkPixbuf'

const MusicContainer = () => Widget.EventBox({
    on_primary_click: () => {
        const player = Mpris.getPlayer('spotify') || Mpris.getPlayer()
        if (!player) return
        player.playPause()
    },
    on_secondary_click: () => {
        const player = Mpris.getPlayer('spotify') || Mpris.getPlayer()
        if (!player) return
        player.next()
    },
    child: Widget.Box({
        class_name: 'bar-music-container',
        spacing: 5,
        children: [
            Widget.CircularProgress({
                class_name: 'music-progress',
                start_at: 0.75,
                child: Widget.Icon({
                    connections: [[Mpris, (icon) => {
                        const player = Mpris.getPlayer('spotify') || Mpris.getPlayer()
                        if (!player) return
                        let icn = icons.mpris.stopped
                        if (player.play_back_status === 'Playing')
                            icn = icons.mpris.playing
                        else if (player.play_back_status === 'Paused')
                            icn = icons.mpris.paused
                        icon.icon = icn
                    }]]
                }),
                connections: [
                    [Mpris, (prog) => {
                        const player = Mpris.getPlayer('spotify') || Mpris.getPlayer()
                        if (!player) return
                        prog.value = player.position / player.length
                    }],
                    [1000, (prog) => {
                        const player = Mpris.getPlayer('spotify') || Mpris.getPlayer()
                        if (!player) return
                        prog.value = player.position / player.length
                    }]
                ]
            }),
            Widget.Label({
                max_width_chars: 35,
                truncate: "end",
                connections: [[Mpris, (label) => {
                    const player = Mpris.getPlayer('spotify') || Mpris.getPlayer()
                    if (!player) return;
                    label.label = player?.track_title + " - " + player?.track_artists
                }]]
            })
        ]
    })
})
const MusicBarContainer = () => Widget.Box({
    hexpand: true,
    children: [
        RoundedAngleEnd("topleft", {class_name: 'angle'}),
        MusicContainer(),
        RoundedAngleEnd("topright", {class_name: 'angle'})
    ],
})

const MusicBarContainerRevealer = () => {
    const box = Widget.Box({
        vertical: false,
        vpack: 'start',
    })
    box.pack_start(Widget.Revealer({
        child: MusicBarContainer(),
        transition: 'slide_down',
        transition_duration: 200,
        binds: [['reveal_child', Mpris, 'players', out => out.length > 0]]
    }), false, false, 0)
    return box;
}
export default MusicBarContainerRevealer;
