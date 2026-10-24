extends Node
## Holes past the first come in their own resource packs on the web (tools/pack_holes.gd makes them,
## tools/web_pack.py hosts them as hole_<id>.pck.wasm beside the page), so the game starts without
## downloading the whole course. An autoload: `await Holes.fetch("h04")` before building a hole, and
## Holes.prefetch(next_id) while one is played so the next is usually there already. Anywhere the
## holes are part of the project (desktop, the editor, the tests) every hole is simply ready.

signal done(id: String, ok: bool)

var _loading := {}       # id -> true while its download runs
var _req := {}           # id -> its HTTPRequest while one runs (the fallback download)
var _got := {}           # id -> [bytes received, bytes in all (0: not known)] while the page fetches it

## The page fetches the pack itself, the way it fetches the game's own files, and hands the bytes to
## the engine's in-memory file system: no browser storage involved (a page shown inside another, like
## the Claude preview, may not be allowed any), and it works wherever the game itself downloaded.
const PAGE_FETCH := """(function (id) {
  window.__holes = window.__holes || {};
  const st = { done: false, ok: false, loaded: 0, total: 0, err: '' };
  window.__holes[id] = st;
  if (typeof engine === 'undefined' || !engine.copyToFS) { st.err = 'noengine'; st.done = true; return; }
  fetch('hole_' + id + '.pck.wasm').then((r) => {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    st.total = +(r.headers.get('content-length') || 0);
    const rd = r.body.getReader();
    const parts = [];
    const pump = () => rd.read().then(({ done, value }) => {
      if (done) return;
      parts.push(value);
      st.loaded += value.length;
      return pump();
    });
    return pump().then(() => {
      const buf = new Uint8Array(st.loaded);
      let o = 0;
      for (const p of parts) { buf.set(p, o); o += p.length; }
      engine.copyToFS('/tmp/hole_' + id + '.pck', buf);
      st.ok = true;
      st.done = true;
    });
  }).catch((e) => { st.err = String((e && e.message) || e); st.done = true; });
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


## True once the hole's files can be loaded.
func is_ready(id: String) -> bool:
	return ResourceLoader.exists("res://assets/holes/%s/hole.glb" % id)


## Download and mount the hole's pack if it isn't here yet; true when it's ready.
func fetch(id: String) -> bool:
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


## Start fetching a hole in the background (nothing to wait for).
func prefetch(id: String) -> void:
	if not is_ready(id) and OS.has_feature("web") and not _loading.has(id):
		_download(id)


func _download(id: String) -> void:
	_loading[id] = true
	var ok := false
	for attempt in 3:
		var got := await _page_fetch(id)
		if got == "noengine":
			break                        # not our page: the engine's own download below
		if got == "":
			ok = ProjectSettings.load_resource_pack("/tmp/hole_%s.pck" % id) and is_ready(id)
			if ok:
				break
		await get_tree().create_timer(1.0 + attempt).timeout
	_got.erase(id)
	if ok:
		_loading.erase(id)
		done.emit(id, true)
		return
	var file := "user://hole_%s.pck" % id
	for attempt in 3:
		var req := HTTPRequest.new()
		add_child(req)
		_req[id] = req
		req.download_file = file
		var url := str(JavaScriptBridge.eval("new URL('hole_%s.pck.wasm', document.baseURI).href" % id, true))
		if req.request(url) == OK:
			var res: Array = await req.request_completed
			ok = res[0] == HTTPRequest.RESULT_SUCCESS and res[1] == 200
		_req.erase(id)
		req.queue_free()
		if ok:
			ok = ProjectSettings.load_resource_pack(file) and is_ready(id)
			if ok:
				break
		await get_tree().create_timer(1.0 + attempt).timeout
	_loading.erase(id)
	done.emit(id, ok)


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
