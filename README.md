# FAQ

> What does this do?

It is a helper script for achieving [Multi-Pointer-X](https://wiki.archlinux.org/index.php/Multi-pointer_X). By default, all pointing devices control the same, single pointer. All keyboards contribute events to the same, global keyboard focus. Using Xorg with Hecaton allows you to have multiple active cursors and keyboard focuses at the same time.

> Multiple cursors? How does that work? 

[XInput2](https://www.x.org/releases/X11R7.7/doc/inputproto/XI2proto.txt), merged into core Xorg in 2009, is a reworking of the input stack. It introduces the concept of an explicit device hierarchy, where each master device is a separate pointer/focus pair, and slave devices can be added to actually control them.

However, setting it up is kinda annoying. On regular Xorg, each connected device gets assigned to the same, single master pointer/keyboard, and it takes a couple of `xinput` invocations to make a standalone pointer out of it. Doing it each time a device connects or disconnects is repetitive and boring.

> How useful is that?

Currently, not very. Most programs are completely unprepared for multiple pointers, and get confused when it appears like the mouse cursor has a split personality. True support would require explicitly supporting XInput2 events, and not only core (regular old single-pointer) events. This is platform-specific and not portable to other systems.

> So can I work in two different programs at once?

That depends on the program. Generally, two windows of a single program (e.g. browser windows) won't work well. Two different browsers, or separate instances of the same browser may be fine, you'll be able to click and scroll both simultaneously.

Keyboards, however, have even more issues. Most programs behave like there's a single, global set of modifiers, and only accept them from one keyboard. Which means that you can't, for example, type uppercased text the other keyboard. Other than that, windows do receive focus from different pointers and inputs from the two keyboards are not mixed.

> So is there anything that works well with it?

To my knowledge, not yet. There was [multicursor-wm](http://multicursor-wm.sourceforge.net/), but it has been defunct for a long time now.

However, a use case for this may be games. One historical example comes to mind: Settlers II for PC, an MS-DOS game from 1996, had a split-screen mode for two players, where the other player used a [second mouse](https://en.wikipedia.org/wiki/The_Settlers_II#Game_modes), completely independent of the first one. This was in pre-USB times, so the game had to include its own mouse drivers.

> Why the name?

[Hecatoncheires](https://mythology.wikia.org/wiki/Hecatoncheires) are giants from Greek mythology, children of proto-gods Gaia and Uranus. Each one had a hundred hands and fifty heads. In fact, _hecto_ as used in the SI prefix system to mean a multiple of 100, derives exactly from Greek ἑκατόν _hekaton_.

To operate all these new cursors simultaneously, a hundred arms and fifty heads would be nice. Hence the name, truncated a bit.

# Design

This is a systemd service, intended to be launched in the user's session (and using their system manager instance, not the main one). It runs [inputplug](https://github.com/andrewshadura/inputplug/), which observes XInput2 events, and dispatches to another program to handle them. That other program is a Python script, with no dependencies other than a standard Python 3 install. In turn, that script knows how to invoke `xinput` to create more master pointers and reassign devices to them.

# Dependencies

* a systemd-based distribution. Most popular Linux distros have been using systemd for many years now.
* an Xorg-based desktop. Wayland won't work, because it has a very different input stack.
* `inputplug`'s build requirements. In terms of Debian packages, these are `libx11-dev`, `libxcb1-dev`, `libxi-dev`, `build-essential`.
* the `xinput` command, usually ships in a package of the same name. Sometimes preinstalled together with Xorg.
* Python 3.6 or newer.

# Installation

1. clone the repository
2. run `git submodule init` then `git submodule update` to fetch inputplug
3. run `make`
4. if necessary, adjust installation paths in the Makefile. By default, both inputplug and the script are installed under user's home directory, so root access is never required.
5. run `make install`
6. start the service with `systemctl --user start hecaton`. To install it permanently, run `systemctl --user enable hecaton`.

# Usage

Just connect an additional mouse/trackball/trackpad after the service is launched. After a brief moment, a new cursor should appear on your screen, and interacting with the newly connected device should move it. Your previous, main cursor will not be affected by this device.

To create a pointer-keyboard pair, connect a keyboard as well. If more devices are connected within a short time window, they form a pair.

## Pairing time window

To keep the program simple, hecaton assigns new master pointers only if the last one was created longer than two minutes ago (configurable in the Python script). This means that to get a keyboard+pointer pair, you should connect both devices within about a minute of each other. Then wait for a minute before connecting more.

This is because the two minutes are successive wall-clock minutes, not time since last connection. If a device was connected at, say, 10:30, then *all* devices (both pointing and keyboards) connected until 10:31:59 will be assigned to the same master pointer/keyboard pair. Devices connected at 10:32:00 or later will form new pairs.

