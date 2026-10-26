extends SceneTree
## Packs each hole's files into its own resource pack, so the web build can fetch a hole only when
## the round reaches it (see scripts/holes.gd). Run after importing:
##   godot --headless --path golf/game -s res://tools/pack_holes.gd -- --out=<dir> --format=etc2 \
##     --split=<build/split.json> h02 h03 ... music
## Each pack holds the hole folder's plain files (heights, surfaces, props, terrain.json) and, for the
## imported ones (the scene, the textures), the .import file and the imported data it points to; plus
## the hole's art left out of the main download (tools/web_split.py). "music" is the songs that come
## after the first, "core" what every hole needs (her frames, the bag, the lanterns, the first song)
## "course" the art all holes share, and "art_<n>" art a few holes share (tools/web_split.py). Textures are kept in one format (--format: etc2 for phones,
## s3tc for desktops),
## each .import cut down to point at that one, so a device downloads only what it reads; the packs
## are named hole_<id>.<format>.pck.
## Files the game never loads (ground.jpg, library.glb: the all-3D experiment) are left out.

const SKIP := ["ground.jpg", "library.glb"]
const FORMATS := ["etc2", "s3tc"]

var _fmt := "etc2"
var _tmp := ""


func _initialize() -> void:
	var out := ""
	var split := {}
	var ids: Array[String] = []
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
		elif a.begins_with("--format="):
			_fmt = a.trim_prefix("--format=")
		elif a.begins_with("--split="):
			split = JSON.parse_string(FileAccess.get_file_as_string(a.trim_prefix("--split=")))
		else:
			ids.append(a)
	DirAccess.make_dir_recursive_absolute(out)
	_tmp = OS.get_cache_dir().path_join("pack_holes_%d" % OS.get_process_id())
	DirAccess.make_dir_recursive_absolute(_tmp)
	for id in ids:
		var pck := PCKPacker.new()
		var path := out.path_join("hole_%s.%s.pck" % [id, _fmt])
		pck.pck_start(path)
		var count := 0
		if id.begins_with("h"):
			var dir := "res://assets/holes/%s/" % id
			for f in DirAccess.get_files_at(dir):
				if f.ends_with(".import") or f.get_basename() in SKIP or f in SKIP or f.ends_with(".uid"):
					continue
				count += _add(pck, dir + f)
		for f: String in split.get("packs", {}).get(id, []):
			count += _add(pck, "res://" + f)
		pck.flush()
		print("%s: %d files, %.1f MB" % [path, count, FileAccess.get_file_as_bytes(path).size() / 1048576.0])
	for f in DirAccess.get_files_at(_tmp):
		DirAccess.remove_absolute(_tmp.path_join(f))
	DirAccess.remove_absolute(_tmp)
	quit()


## One file into the pack: a plain file as it is; an imported one as its .import (cut down to this
## pack's texture format) and the imported data that format reads. How many files went in.
func _add(pck: PCKPacker, res: String) -> int:
	var imp := res + ".import"
	if not FileAccess.file_exists(imp):
		pck.add_file(res, ProjectSettings.globalize_path(res))
		return 1
	var cfg := ConfigFile.new()
	cfg.load(imp)
	var keep: Array = []
	for d: String in cfg.get_value("deps", "dest_files", []):
		var other := false
		for f: String in FORMATS:
			if f != _fmt and d.contains("." + f + "."):
				other = true
		if not other:
			keep.append(d)
	for f: String in FORMATS:
		if f != _fmt and cfg.has_section_key("remap", "path." + f):
			cfg.erase_section_key("remap", "path." + f)
	cfg.set_value("deps", "dest_files", keep)
	var cut := _tmp.path_join(res.md5_text() + ".import")
	cfg.save(cut)
	pck.add_file(imp, cut)
	for d: String in keep:
		pck.add_file(d, ProjectSettings.globalize_path(d))
	return 1 + keep.size()
