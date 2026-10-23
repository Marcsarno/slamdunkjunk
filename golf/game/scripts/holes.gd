extends Node
## Holes past the first come in their own resource packs on the web (tools/pack_holes.gd makes them,
## tools/web_pack.py hosts them as hole_<id>.pck.wasm beside the page), so the game starts without
## downloading the whole course. An autoload: `await Holes.fetch("h04")` before building a hole, and
## Holes.prefetch(next_id) while one is played so the next is usually there already. Anywhere the
## holes are part of the project (desktop, the editor, the tests) every hole is simply ready.

signal done(id: String, ok: bool)

var _loading := {}       # id -> true while its download runs


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
	var file := "user://hole_%s.pck" % id
	for attempt in 3:
		var req := HTTPRequest.new()
		add_child(req)
		req.download_file = file
		var url := str(JavaScriptBridge.eval("new URL('hole_%s.pck.wasm', document.baseURI).href" % id, true))
		if req.request(url) == OK:
			var res: Array = await req.request_completed
			ok = res[0] == HTTPRequest.RESULT_SUCCESS and res[1] == 200
		req.queue_free()
		if ok:
			ok = ProjectSettings.load_resource_pack(file) and is_ready(id)
			if ok:
				break
		await get_tree().create_timer(1.0 + attempt).timeout
	_loading.erase(id)
	done.emit(id, ok)
