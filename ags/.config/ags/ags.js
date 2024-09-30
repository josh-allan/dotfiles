// ../../../../../../usr/share/astal/gjs/src/imports.ts
import { default as default2 } from "gi://Astal?version=0.1";
import { default as default3 } from "gi://GObject?version=2.0";
import { default as default4 } from "gi://Gio?version=2.0";
import { default as default5 } from "gi://Gtk?version=3.0";
import { default as default6 } from "gi://Gdk?version=3.0";
import { default as default7 } from "gi://GLib?version=2.0";

// ../../../../../../usr/share/astal/gjs/src/process.ts
function subprocess(argsOrCmd, onOut = print, onErr = printerr) {
  const args = Array.isArray(argsOrCmd) || typeof argsOrCmd === "string";
  const { cmd, err, out } = {
    cmd: args ? argsOrCmd : argsOrCmd.cmd,
    err: args ? onErr : argsOrCmd.err || onErr,
    out: args ? onOut : argsOrCmd.out || onOut
  };
  const proc = Array.isArray(cmd) ? default2.Process.subprocessv(cmd) : default2.Process.subprocess(cmd);
  proc.connect("stdout", (_, stdout) => out(stdout));
  proc.connect("stderr", (_, stderr) => err(stderr));
  return proc;
}
function execAsync(cmd) {
  return new Promise((resolve, reject) => {
    if (Array.isArray(cmd)) {
      default2.Process.exec_asyncv(cmd, (_, res) => {
        try {
          resolve(default2.Process.exec_asyncv_finish(res));
        } catch (error) {
          reject(error);
        }
      });
    } else {
      default2.Process.exec_async(cmd, (_, res) => {
        try {
          resolve(default2.Process.exec_finish(res));
        } catch (error) {
          reject(error);
        }
      });
    }
  });
}

// ../../../../../../usr/share/astal/gjs/src/time.ts
function interval(interval2, callback) {
  return default2.Time.interval(interval2, () => void callback?.());
}

// ../../../../../../usr/share/astal/gjs/src/binding.ts
var snakeify = (str) => str.replace(/([a-z])([A-Z])/g, "$1_$2").replaceAll("-", "_").toLowerCase();
var kebabify = (str) => str.replace(/([a-z])([A-Z])/g, "$1-$2").replaceAll("_", "-").toLowerCase();
var Binding = class _Binding {
  transformFn = (v) => v;
  #emitter;
  #prop;
  static bind(emitter, prop) {
    return new _Binding(emitter, prop);
  }
  constructor(emitter, prop) {
    this.#emitter = emitter;
    this.#prop = prop && kebabify(prop);
  }
  toString() {
    return `Binding<${this.#emitter}${this.#prop ? `, "${this.#prop}"` : ""}>`;
  }
  as(fn) {
    const bind2 = new _Binding(this.#emitter, this.#prop);
    bind2.transformFn = (v) => fn(this.transformFn(v));
    return bind2;
  }
  get() {
    if (typeof this.#emitter.get === "function")
      return this.transformFn(this.#emitter.get());
    if (typeof this.#prop === "string") {
      const getter = `get_${snakeify(this.#prop)}`;
      if (typeof this.#emitter[getter] === "function")
        return this.transformFn(this.#emitter[getter]());
      return this.transformFn(this.#emitter[this.#prop]);
    }
    throw Error("can not get value of binding");
  }
  subscribe(callback) {
    if (typeof this.#emitter.subscribe === "function") {
      return this.#emitter.subscribe(() => {
        callback(this.get());
      });
    } else if (typeof this.#emitter.connect === "function") {
      const signal = `notify::${this.#prop}`;
      const id = this.#emitter.connect(signal, () => {
        callback(this.get());
      });
      return () => {
        this.#emitter.disconnect(id);
      };
    }
    throw Error(`${this.#emitter} is not bindable`);
  }
};
var { bind } = Binding;

// ../../../../../../usr/share/astal/gjs/src/variable.ts
var VariableWrapper = class extends Function {
  variable;
  errHandler = console.error;
  _value;
  _poll;
  _watch;
  pollInterval = 1e3;
  pollExec;
  pollTransform;
  pollFn;
  watchTransform;
  watchExec;
  constructor(init) {
    super();
    this._value = init;
    this.variable = new default2.VariableBase();
    this.variable.connect("dropped", () => {
      this.stopWatch();
      this.stopPoll();
    });
    this.variable.connect("error", (_, err) => this.errHandler?.(err));
    return new Proxy(this, {
      apply: (target, _, args) => target._call(args[0])
    });
  }
  _call(transform) {
    const b = Binding.bind(this);
    return transform ? b.as(transform) : b;
  }
  toString() {
    return String(`Variable<${this.get()}>`);
  }
  get() {
    return this._value;
  }
  set(value) {
    if (value !== this._value) {
      this._value = value;
      this.variable.emit("changed");
    }
  }
  startPoll() {
    if (this._poll)
      return;
    if (this.pollFn) {
      this._poll = interval(this.pollInterval, () => {
        const v = this.pollFn(this.get());
        if (v instanceof Promise) {
          v.then((v2) => this.set(v2)).catch((err) => this.variable.emit("error", err));
        } else {
          this.set(v);
        }
      });
    } else if (this.pollExec) {
      this._poll = interval(this.pollInterval, () => {
        execAsync(this.pollExec).then((v) => this.set(this.pollTransform(v, this.get()))).catch((err) => this.variable.emit("error", err));
      });
    }
  }
  startWatch() {
    if (this._watch)
      return;
    this._watch = subprocess({
      cmd: this.watchExec,
      out: (out) => this.set(this.watchTransform(out, this.get())),
      err: (err) => this.variable.emit("error", err)
    });
  }
  stopPoll() {
    this._poll?.cancel();
    delete this._poll;
  }
  stopWatch() {
    this._watch?.kill();
    delete this._watch;
  }
  isPolling() {
    return !!this._poll;
  }
  isWatching() {
    return !!this._watch;
  }
  drop() {
    this.variable.emit("dropped");
  }
  onDropped(callback) {
    this.variable.connect("dropped", callback);
    return this;
  }
  onError(callback) {
    delete this.errHandler;
    this.variable.connect("error", (_, err) => callback(err));
    return this;
  }
  subscribe(callback) {
    const id = this.variable.connect("changed", () => {
      callback(this.get());
    });
    return () => this.variable.disconnect(id);
  }
  poll(interval2, exec, transform = (out) => out) {
    this.stopPoll();
    this.pollInterval = interval2;
    this.pollTransform = transform;
    if (typeof exec === "function") {
      this.pollFn = exec;
      delete this.pollExec;
    } else {
      this.pollExec = exec;
      delete this.pollFn;
    }
    this.startPoll();
    return this;
  }
  watch(exec, transform = (out) => out) {
    this.stopWatch();
    this.watchExec = exec;
    this.watchTransform = transform;
    this.startWatch();
    return this;
  }
  observe(objs, sigOrFn, callback) {
    const f = typeof sigOrFn === "function" ? sigOrFn : callback ?? (() => this.get());
    const set = (obj, ...args) => this.set(f(obj, ...args));
    if (Array.isArray(objs)) {
      for (const obj of objs) {
        const [o, s] = obj;
        const id = o.connect(s, set);
        this.onDropped(() => o.disconnect(id));
      }
    } else {
      if (typeof sigOrFn === "string") {
        const id = objs.connect(sigOrFn, set);
        this.onDropped(() => objs.disconnect(id));
      }
    }
    return this;
  }
  static derive(deps, fn = (...args) => args) {
    const update = () => fn(...deps.map((d) => d.get()));
    const derived = new Variable(update());
    const unsubs = deps.map((dep) => dep.subscribe(() => derived.set(update())));
    derived.onDropped(() => unsubs.map((unsub) => unsub()));
    return derived;
  }
};
var Variable = new Proxy(VariableWrapper, {
  apply: (_t, _a, args) => new VariableWrapper(args[0])
});
var variable_default = Variable;

// ../../../../../../usr/share/astal/gjs/src/astalify.ts
Object.defineProperty(default2.Box.prototype, "children", {
  get() {
    return this.get_children();
  },
  set(v) {
    this.set_children(v);
  }
});
function setChildren(parent, children) {
  children = children.flat(Infinity).map((ch) => ch instanceof default5.Widget ? ch : new default5.Label({ visible: true, label: String(ch) }));
  if (parent instanceof default5.Bin) {
    const ch = parent.get_child();
    if (ch)
      parent.remove(ch);
  } else if (parent instanceof default5.Container && !(parent instanceof default2.Box || parent instanceof default2.Stack)) {
    for (const ch of parent.get_children())
      parent.remove(ch);
  }
  if (parent instanceof default2.Box) {
    parent.set_children(children);
  } else if (parent instanceof default2.Stack) {
    parent.set_children(children);
  } else if (parent instanceof default2.CenterBox) {
    parent.startWidget = children[0];
    parent.centerWidget = children[1];
    parent.endWidget = children[2];
  } else if (parent instanceof default2.Overlay) {
    const [child, ...overlays] = children;
    parent.set_child(child);
    parent.set_overlays(overlays);
  } else if (parent instanceof default5.Container) {
    for (const ch of children)
      parent.add(ch);
  }
}
function mergeBindings(array) {
  function getValues(...args) {
    let i = 0;
    return array.map(
      (value) => value instanceof Binding ? args[i++] : value
    );
  }
  const bindings = array.filter((i) => i instanceof Binding);
  if (bindings.length === 0)
    return array;
  if (bindings.length === 1)
    return bindings[0].as(getValues);
  return variable_default.derive(bindings, getValues)();
}
function setProp(obj, prop, value) {
  try {
    const setter = `set_${snakeify(prop)}`;
    if (typeof obj[setter] === "function")
      return obj[setter](value);
    if (Object.hasOwn(obj, prop))
      return obj[prop] = value;
  } catch (error) {
    console.error(`could not set property "${prop}" on ${obj}:`, error);
  }
  console.error(`could not set property "${prop}" on ${obj}`);
}
function hook(self, object, signalOrCallback, callback) {
  if (typeof object.connect === "function" && callback) {
    const id = object.connect(signalOrCallback, (_, ...args) => {
      callback(self, ...args);
    });
    self.connect("destroy", () => {
      object.disconnect(id);
    });
  } else if (typeof object.subscribe === "function" && typeof signalOrCallback === "function") {
    const unsub = object.subscribe((...args) => {
      signalOrCallback(self, ...args);
    });
    self.connect("destroy", unsub);
  }
  return self;
}
function ctor(self, config = {}, children = []) {
  const { setup, ...props } = config;
  props.visible ??= true;
  const bindings = Object.keys(props).reduce((acc, prop) => {
    if (props[prop] instanceof Binding) {
      const binding = props[prop];
      delete props[prop];
      return [...acc, [prop, binding]];
    }
    return acc;
  }, []);
  const onHandlers = Object.keys(props).reduce((acc, key) => {
    if (key.startsWith("on")) {
      const sig = kebabify(key).split("-").slice(1).join("-");
      const handler = props[key];
      delete props[key];
      return [...acc, [sig, handler]];
    }
    return acc;
  }, []);
  children = mergeBindings(children.flat(Infinity));
  if (children instanceof Binding) {
    setChildren(self, children.get());
    self.connect("destroy", children.subscribe((v) => {
      setChildren(self, v);
    }));
  } else {
    if (children.length > 0) {
      setChildren(self, children);
    }
  }
  for (const [signal, callback] of onHandlers) {
    if (typeof callback === "function") {
      self.connect(signal, callback);
    } else {
      self.connect(signal, () => execAsync(callback).then(print).catch(console.error));
    }
  }
  for (const [prop, binding] of bindings) {
    if (prop === "child" || prop === "children") {
      self.connect("destroy", binding.subscribe((v) => {
        setChildren(self, v);
      }));
    }
    self.connect("destroy", binding.subscribe((v) => {
      setProp(self, prop, v);
    }));
    setProp(self, prop, binding.get());
  }
  Object.assign(self, props);
  setup?.(self);
  return self;
}
function proxify(klass) {
  Object.defineProperty(klass.prototype, "className", {
    get() {
      return default2.widget_get_class_names(this).join(" ");
    },
    set(v) {
      default2.widget_set_class_names(this, v.split(/\s+/));
    }
  });
  Object.defineProperty(klass.prototype, "css", {
    get() {
      return default2.widget_get_css(this);
    },
    set(v) {
      default2.widget_set_css(this, v);
    }
  });
  Object.defineProperty(klass.prototype, "cursor", {
    get() {
      return default2.widget_get_cursor(this);
    },
    set(v) {
      default2.widget_set_cursor(this, v);
    }
  });
  Object.defineProperty(klass.prototype, "clickThrough", {
    get() {
      return default2.widget_get_click_through(this);
    },
    set(v) {
      default2.widget_set_click_through(this, v);
    }
  });
  Object.assign(klass.prototype, {
    hook: function(obj, sig, callback) {
      return hook(this, obj, sig, callback);
    },
    toggleClassName: function name(cn, cond = true) {
      default2.widget_toggle_class_name(this, cn, cond);
    },
    set_class_name: function(name) {
      this.className = name;
    },
    set_css: function(css) {
      this.css = css;
    },
    set_cursor: function(cursor) {
      this.cursor = cursor;
    },
    set_click_through: function(clickThrough) {
      this.clickThrough = clickThrough;
    }
  });
  const proxy = new Proxy(klass, {
    construct(_, [conf, ...children]) {
      return ctor(new klass(), conf, children);
    },
    apply(_t, _a, [conf, ...children]) {
      return ctor(new klass(), conf, children);
    }
  });
  return proxy;
}
function astalify(klass) {
  return proxify(klass);
}

// ../../../../../../usr/share/astal/gjs/src/widgets.ts
var Box = astalify(default2.Box);
var Button = astalify(default2.Button);
var CenterBox = astalify(default2.CenterBox);
var CircularProgress = astalify(default2.CircularProgress);
var DrawingArea = astalify(default5.DrawingArea);
var Entry = astalify(default5.Entry);
var EventBox = astalify(default2.EventBox);
var Icon = astalify(default2.Icon);
var Label = astalify(default2.Label);
var LevelBar = astalify(default2.LevelBar);
var Overlay = astalify(default2.Overlay);
var Revealer = astalify(default5.Revealer);
var Scrollable = astalify(default2.Scrollable);
var Slider = astalify(default2.Slider);
var Stack = astalify(default2.Stack);
var Switch = astalify(default5.Switch);
var Window = astalify(default2.Window);

// ../../../../../../usr/share/astal/gjs/src/application.ts
import { setConsoleLogDomain } from "console";
import { exit, programArgs } from "system";
var application_default = new class AstalJS extends default2.Application {
  static {
    default3.registerClass(this);
  }
  eval(body) {
    return new Promise((res, rej) => {
      try {
        const fn = Function(`return (async function() {
                    ${body.includes(";") ? body : `return ${body};`}
                })`);
        fn()().then(res).catch(rej);
      } catch (error) {
        rej(error);
      }
    });
  }
  requestHandler;
  vfunc_request(msg, conn) {
    if (typeof this.requestHandler === "function") {
      this.requestHandler(msg, (response) => {
        default2.write_sock(
          conn,
          String(response),
          (_, res) => default2.write_sock_finish(res)
        );
      });
    } else {
      super.vfunc_request(msg, conn);
    }
  }
  apply_css(style, reset = false) {
    super.apply_css(style, reset);
  }
  quit(code) {
    super.quit();
    exit(code ?? 0);
  }
  start({ requestHandler, css, hold, main, client, icons, ...cfg } = {}) {
    client ??= () => {
      print(`Astal instance "${this.instanceName}" already running`);
      exit(1);
    };
    Object.assign(this, cfg);
    setConsoleLogDomain(this.instanceName);
    this.requestHandler = requestHandler;
    this.connect("activate", () => {
      const path = import.meta.url.split("/").slice(3);
      const file = path.at(-1).replace(".js", ".css");
      const css2 = `/${path.slice(0, -1).join("/")}/${file}`;
      if (file.endsWith(".css") && default7.file_test(css2, default7.FileTest.EXISTS))
        this.apply_css(css2, false);
      main?.(...programArgs);
    });
    if (!this.acquire_socket())
      return client((msg) => default2.Application.send_message(this.instanceName, msg), ...programArgs);
    if (css)
      this.apply_css(css, false);
    if (icons)
      this.add_icons(icons);
    hold ??= true;
    if (hold)
      this.hold();
    this.runAsync([]);
  }
}();

// ../../../../../../usr/share/astal/gjs/index.ts
default5.init(null);

// sass:/home/josh/.dotfiles/ags/.config/ags/style.scss
var style_default = "window.Bar {\n  border: none;\n  box-shadow: none;\n  background-color: #212223;\n  color: #f1f1f1;\n  font-size: 1.1em;\n  font-weight: bold;\n}\nwindow.Bar button {\n  all: unset;\n  background-color: transparent;\n}\nwindow.Bar button:hover label {\n  background-color: rgba(241, 241, 241, 0.16);\n  border-color: rgba(55, 141, 247, 0.2);\n}\nwindow.Bar button:active label {\n  background-color: rgba(241, 241, 241, 0.2);\n}\nwindow.Bar label {\n  transition: 200ms;\n  padding: 0 8px;\n  margin: 2px;\n  border-radius: 7px;\n  border: 1pt solid transparent;\n}\nwindow.Bar .Workspaces .focused label {\n  color: #378DF7;\n  border-color: #378DF7;\n}\nwindow.Bar .FocusedClient {\n  color: #378DF7;\n}\nwindow.Bar .Media .Cover {\n  min-height: 1.2em;\n  min-width: 1.2em;\n  border-radius: 7px;\n  background-position: center;\n  background-size: contain;\n}\nwindow.Bar .Network label {\n  padding-left: 0;\n  margin-left: 0;\n}\nwindow.Bar .Battery label {\n  padding-left: 0;\n  margin-left: 0;\n}\nwindow.Bar .AudioSlider {\n  margin: 0 1em;\n}\nwindow.Bar .AudioSlider * {\n  all: unset;\n}\nwindow.Bar .AudioSlider icon {\n  margin-right: 0.6em;\n}\nwindow.Bar .AudioSlider trough {\n  background-color: rgba(241, 241, 241, 0.2);\n  border-radius: 7px;\n}\nwindow.Bar .AudioSlider highlight {\n  background-color: #378DF7;\n  min-height: 0.8em;\n  border-radius: 7px;\n}\nwindow.Bar .AudioSlider slider {\n  background-color: #f1f1f1;\n  border-radius: 7px;\n  min-height: 1em;\n  min-width: 1em;\n  margin: -0.2em;\n}";

// widget/Bar.tsx
import Hyprland from "gi://AstalHyprland";
import Battery from "gi://AstalBattery";
import Wp from "gi://AstalWp";
import Network from "gi://AstalNetwork";
import Tray from "gi://AstalTray";

// ../../../../../../usr/share/astal/gjs/src/jsx/jsx-runtime.ts
function isArrowFunction(func) {
  return !Object.hasOwn(func, "prototype");
}
function jsx(ctor2, { children, ...props }) {
  children ??= [];
  if (!Array.isArray(children))
    children = [children];
  children = children.filter(Boolean);
  if (typeof ctor2 === "string")
    return ctors[ctor2](props, children);
  if (children.length === 1)
    props.child = children[0];
  else if (children.length > 1)
    props.children = children;
  if (isArrowFunction(ctor2))
    return ctor2(props);
  return new ctor2(props);
}
var ctors = {
  box: Box,
  button: Button,
  centerbox: CenterBox,
  circularprogress: CircularProgress,
  drawingarea: DrawingArea,
  entry: Entry,
  eventbox: EventBox,
  // TODO: fixed
  // TODO: flowbox
  icon: Icon,
  label: Label,
  levelbar: LevelBar,
  // TODO: listbox
  overlay: Overlay,
  revealer: Revealer,
  scrollable: Scrollable,
  slider: Slider,
  stack: Stack,
  switch: Switch,
  window: Window
};
var jsxs = jsx;

// widget/Bar.tsx
function SysTray() {
  const tray = Tray.get_default();
  return /* @__PURE__ */ jsx("box", { children: bind(tray, "items").as((items) => items.map((item) => {
    if (item.iconThemePath)
      application_default.add_icons(item.iconThemePath);
    const menu = item.create_menu();
    return /* @__PURE__ */ jsx(
      "button",
      {
        tooltipMarkup: bind(item, "tooltipMarkup"),
        onDestroy: () => menu?.destroy(),
        onClickRelease: (self) => {
          menu?.popup_at_widget(self, default6.Gravity.SOUTH, default6.Gravity.NORTH, null);
        },
        children: /* @__PURE__ */ jsx("icon", { gIcon: bind(item, "gicon") })
      }
    );
  })) });
}
function Wifi() {
  const { wifi } = Network.get_default();
  return /* @__PURE__ */ jsx(
    "icon",
    {
      tooltipText: bind(wifi, "ssid").as(String),
      className: "Wifi",
      icon: bind(wifi, "iconName")
    }
  );
}
function AudioSlider() {
  const speaker = Wp.get_default()?.audio.defaultSpeaker;
  return /* @__PURE__ */ jsxs("box", { className: "AudioSlider", css: "min-width: 140px", children: [
    /* @__PURE__ */ jsx("icon", { icon: bind(speaker, "volumeIcon") }),
    /* @__PURE__ */ jsx(
      "slider",
      {
        hexpand: true,
        onDragged: ({ value }) => speaker.volume = value,
        value: bind(speaker, "volume")
      }
    )
  ] });
}
function BatteryLevel() {
  const bat = Battery.get_default();
  return /* @__PURE__ */ jsxs(
    "box",
    {
      className: "Battery",
      visible: bind(bat, "isPresent"),
      children: [
        /* @__PURE__ */ jsx("icon", { icon: bind(bat, "batteryIconName") }),
        /* @__PURE__ */ jsx("label", { label: bind(bat, "percentage").as(
          (p) => `${Math.floor(p * 100)} %`
        ) })
      ]
    }
  );
}
function Workspaces() {
  const hypr = Hyprland.get_default();
  return /* @__PURE__ */ jsx("box", { className: "Workspaces", children: bind(hypr, "workspaces").as(
    (wss) => wss.sort((a, b) => a.id - b.id).map((ws) => /* @__PURE__ */ jsx(
      "button",
      {
        className: bind(hypr, "focusedWorkspace").as((fw) => ws === fw ? "focused" : ""),
        onClicked: () => ws.focus(),
        children: ws.id
      }
    ))
  ) });
}
function FocusedClient() {
  const hypr = Hyprland.get_default();
  const focused = bind(hypr, "focusedClient");
  return /* @__PURE__ */ jsx(
    "box",
    {
      className: "Focused",
      visible: focused.as(Boolean),
      children: focused.as((client) => client && /* @__PURE__ */ jsx("label", { label: bind(client, "title").as(String) }))
    }
  );
}
function Time({ format = "%H:%M - %A %e." }) {
  const time = Variable("").poll(1e3, () => default7.DateTime.new_now_local().format(format));
  return /* @__PURE__ */ jsx(
    "label",
    {
      className: "Time",
      onDestroy: () => time.drop(),
      label: time()
    }
  );
}
function Bar(monitor) {
  const anchor = default2.WindowAnchor.TOP | default2.WindowAnchor.LEFT | default2.WindowAnchor.RIGHT;
  return /* @__PURE__ */ jsx(
    "window",
    {
      className: "Bar",
      gdkmonitor: monitor,
      exclusivity: default2.Exclusivity.EXCLUSIVE,
      anchor,
      children: /* @__PURE__ */ jsxs("centerbox", { children: [
        /* @__PURE__ */ jsx("box", { hexpand: true, halign: default5.Align.START, children: /* @__PURE__ */ jsx(Workspaces, {}) }),
        /* @__PURE__ */ jsx("box", { children: /* @__PURE__ */ jsx(FocusedClient, {}) }),
        /* @__PURE__ */ jsxs("box", { hexpand: true, halign: default5.Align.END, children: [
          /* @__PURE__ */ jsx(SysTray, {}),
          /* @__PURE__ */ jsx(Wifi, {}),
          /* @__PURE__ */ jsx(AudioSlider, {}),
          /* @__PURE__ */ jsx(BatteryLevel, {}),
          /* @__PURE__ */ jsx(Time, {})
        ] })
      ] })
    }
  );
}

// app.ts
application_default.start({
  css: style_default,
  main: () => application_default.get_monitors().map(Bar)
});
