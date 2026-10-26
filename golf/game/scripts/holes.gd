extends Node
## On the web the game's first download is only the title and the clubhouse: what every hole needs
## ("core") and each hole come in their own resource packs (tools/pack_holes.gd makes them, with each
## hole's own trees, skies and ground art, and "music", the songs after the first;
## tools/web_pack.py hosts them gzipped as hole_<id>.<format>.pck.wasm beside the page), so the game
## starts without downloading the whole course. An autoload: `await Holes.fetch("h04")` before
## building a hole, and Holes.queue([...]) while one is played to fetch the rest one after another
## in the background. Anywhere the holes are part of the project (desktop, the editor, the tests)
## every hole is simply ready.

signal done(id: String, ok: bool)

var _loading := {}       # id -> true while its download runs
var _req := {}           # id -> its HTTPRequest while one runs (the fallback download)
var _got := {}           # id -> [bytes received, bytes in all (0: not known)] while the page fetches it
var _mounted := {}       # id -> true once its pack is in (the web)
var _queue: Array = []   # what's still to fetch in the background, in order
var _queue_running := false
## While true a finished download waits before it's unpacked and mounted (both stall the game for a
## moment): main.gd holds it through the opening, the swing and the ball's flight, so the hitch lands
## while she stands lining up a shot or in the menus, never mid-swing.
var hold := false

## The page fetches the pack itself, the way it fetches the game's own files, and hands the bytes to
## the engine's in-memory file system: no browser storage involved (a page shown inside another, like
## the Claude preview, may not be allowed any), and it works wherever the game itself downloaded.
const PAGE_FETCH := """(function (id) {
  window.__holes = window.__holes || {};
  const st = { done: false, ok: false, loaded: 0, total: 0, err: '' };
  window.__holes[id] = st;
  if (typeof engine === 'undefined' || !engine.copyToFS) { st.err = 'noengine'; st.done = true; return; }
  // in the texture format this device reads (the page's loader picked it for the game's own data);
  // hosted gzipped: counted as it arrives (for the bar), unzipped on the way in
  fetch('hole_' + id + '.' + (window.__texfmt || 'etc2') + '.pck.wasm').then((r) => {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    st.total = +(r.headers.get('content-length') || 0);
    const counted = r.body.pipeThrough(new TransformStream({
      transform(chunk, ctrl) { st.loaded += chunk.length; ctrl.enqueue(chunk); },
    }));
    const rd = counted.pipeThrough(new DecompressionStream('gzip')).getReader();
    const parts = [];
    let size = 0;
    const pump = () => rd.read().then(({ done, value }) => {
      if (done) return;
      parts.push(value);
      size += value.length;
      return pump();
    });
    return pump().then(() => {
      const buf = new Uint8Array(size);
      let o = 0;
      for (const p of parts) { buf.set(p, o); o += p.length; }
      // kept apart from the status (which the game reads as text) until a calm moment (see MOUNT)
      window.__holebufs = window.__holebufs || {};
      window.__holebufs[id] = buf;
      st.ok = true;
      st.done = true;
    });
  }).catch((e) => { st.err = String((e && e.message) || e); st.done = true; });
})('%s');"""


## A downloaded pack into the engine's memory file system (a short freeze on a phone for a big one).
const MOUNT := """(function (id) {
  const bufs = window.__holebufs || {};
  if (bufs[id]) { engine.copyToFS('/tmp/hole_' + id + '.pck', bufs[id]); delete bufs[id]; }
})('%s');"""


## How much of a hole's download has arrived, 0..1, or -1 when its size isn't known (a browser may not
## say until it's done).
func progress(id: String) -> float:
	if _got.has(id):
		return -1.0 if _got[id][1] <= 0 else clampf(float(_got[id][0]) / float(_got[id][1]), 0.0, 1.0)
	var r: HTTPRequest = _req.get(id)
	if r == null or r.get_body_size() <= 0:
		return -1.0
	return clampf(float(r.get_downloaded_bytes()) / float(r.get_body_size()), 0.0, 1.0)


## Bytes of a hole's download received so far.
func downloaded(id: String) -> int:
	if _got.has(id):
		return int(_got[id][0])
	var r: HTTPRequest = _req.get(id)
	return r.get_downloaded_bytes() if r != null else 0


## True once a pack's files can be loaded: on the web once it's downloaded and mounted; anywhere else
## everything is part of the game already.
func is_ready(id: String) -> bool:
	if OS.has_feature("web"):
		return _mounted.has(id)
	if id.begins_with("art_"):
		return true
	match id:
		"core", "course": return true
		"music": return ResourceLoader.exists(Music.SONGS[-1])
	return ResourceLoader.exists("res://assets/holes/%s/hole.glb" % id)


## The packs a hole needs, in the order they're fetched: what every hole needs, the art all holes
## share, the art it shares with a few others (each downloaded once, for the first of them), its own.
func needs(id: String) -> Array:
	return ["core", "course"] + _art_deps().get(id, []) + [id]


var _deps: Variant = null


## Which "art_" packs each hole needs (tools/web_split.py writes it with the web build).
func _art_deps() -> Dictionary:
	if _deps == null:
		var f := "res://assets/pack_deps.json"
		_deps = JSON.parse_string(FileAccess.get_file_as_string(f)) if FileAccess.file_exists(f) else {}
		if not _deps is Dictionary:
			_deps = {}
	return _deps


## True once a hole can be built.
func hole_ready(id: String) -> bool:
	return needs(id).all(is_ready)


## Download and mount the hole's pack if it isn't here yet (and the core one first, for a hole); true
## when it's ready.
func fetch(id: String) -> bool:
	if id.begins_with("h"):
		# its shared art comes in several small packs: start them all at once, so a phone waits for
		# one round trip, not one each
		for dep: String in needs(id):
			if dep.begins_with("art_") and OS.has_feature("web") and not is_ready(dep) and not _loading.has(dep):
				_download(dep)
		for dep: String in needs(id):
			if dep != id and not await fetch(dep):
				return false
	if is_ready(id):
		return true
	if not OS.has_feature("web"):
		return false
	if not _loading.has(id):
		_download(id)
	while true:
		var r: Array = await done
		if r[0] == id:
			return r[1]
	return false


## Fetch these in the background, one after another in this order (replacing what was still to come),
## so a slow connection spends itself on the next hole first and never on several at once.
func queue(ids: Array) -> void:
	_queue = []
	for id: String in ids:                   # a hole with the packs it needs first (its shared art)
		for p: String in (needs(id) if id.begins_with("h") else [id]):
			if not p in _queue:
				_queue.append(p)
	if not _queue_running and OS.has_feature("web"):
		_run_queue()


func _run_queue() -> void:
	_queue_running = true
	while not _queue.is_empty():
		var id: String = _queue.pop_front()
		if is_ready(id):
			continue
		if _loading.has(id):
			while true:                 # already on its way (the round got there first): wait for it
				var r: Array = await done
				if r[0] == id:
					break
		else:
			await _download(id)
	_queue_running = false


func _download(id: String) -> void:
	_loading[id] = true
	var ok := false
	for attempt in 3:
		var got := await _page_fetch(id)
		if got == "noengine":
			break                        # not our page: the engine's own download below
		if got == "":
			await _calm()
			JavaScriptBridge.eval(MOUNT % id, true)
			ok = ProjectSettings.load_resource_pack("/tmp/hole_%s.pck" % id)
			if ok:
				break
		await get_tree().create_timer(1.0 + attempt).timeout
	_got.erase(id)
	if ok:
		_mounted[id] = true
		_loading.erase(id)
		done.emit(id, true)
		return
	var file := "user://hole_%s.pck" % id
	for attempt in 3:
		var req := HTTPRequest.new()
		add_child(req)
		_req[id] = req
		req.download_file = file
		var url := str(JavaScriptBridge.eval("new URL('hole_%s.' + (window.__texfmt || 'etc2') + '.pck.wasm', document.baseURI).href" % id, true))
		if req.request(url) == OK:
			var res: Array = await req.request_completed
			ok = res[0] == HTTPRequest.RESULT_SUCCESS and res[1] == 200
		_req.erase(id)
		req.queue_free()
		if ok:
			await _calm()
			# hosted gzipped: unzip it in place before mounting
			var raw := FileAccess.get_file_as_bytes(file).decompress_dynamic(-1, FileAccess.COMPRESSION_GZIP)
			var w := FileAccess.open(file, FileAccess.WRITE)
			ok = raw.size() > 0 and w != null
			if ok:
				w.store_buffer(raw)
				w.close()
		if ok:
			ok = ProjectSettings.load_resource_pack(file)
			if ok:
				break
		await get_tree().create_timer(1.0 + attempt).timeout
	if ok:
		_mounted[id] = true
	_loading.erase(id)
	done.emit(id, ok)


var _kept := {}          # resources loaded ahead (warm), held so they stay loaded until the hole is built


## Load a hole's course ahead, in the background, while the player is in the clubhouse: building the
## hole then finds it already loaded.
func warm(id: String) -> void:
	var path := "res://assets/holes/%s/hole.glb" % id
	if _kept.has(path) or not hole_ready(id):
		return
	_kept[path] = null
	if ResourceLoader.load_threaded_request(path) != OK:
		_kept.erase(path)
		return
	while ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
		await get_tree().process_frame
	if ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_LOADED:
		_kept[path] = ResourceLoader.load_threaded_get(path)


## Wait until nothing on screen would stutter (see hold).
func _calm() -> void:
	while hold:
		await get_tree().process_frame


## Have the page fetch the pack into the engine's memory; "" when it's there, else what went wrong.
func _page_fetch(id: String) -> String:
	_got[id] = [0, 0]
	JavaScriptBridge.eval(PAGE_FETCH % id, true)
	while true:
		await get_tree().create_timer(0.1).timeout
		var st: Variant = JSON.parse_string(str(JavaScriptBridge.eval("JSON.stringify((window.__holes || {})['%s'] || null)" % id, true)))
		if not (st is Dictionary):
			return "lost"
		_got[id] = [int(st.loaded), int(st.total)]
		if st.done:
			return "" if st.ok else str(st.err)
	return "lost"
