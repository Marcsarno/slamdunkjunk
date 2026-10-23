extends SceneTree
## Packs each hole's files into its own resource pack, so the web build can fetch a hole only when
## the round reaches it (see scripts/holes.gd). Run after importing:
##   godot --headless --path golf/game -s res://tools/pack_holes.gd -- --out=<dir> h02 h03 ...
## Each pack holds the hole folder's plain files (heights, surfaces, props, terrain.json) and, for the
## imported ones (the scene, the textures), the .import file and the imported data it points to.
## Files the game never loads (ground.jpg, library.glb: the all-3D experiment) are left out.

const SKIP := ["ground.jpg", "library.glb"]


func _initialize() -> void:
	var out := ""
	var ids: Array[String] = []
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
		else:
			ids.append(a)
	DirAccess.make_dir_recursive_absolute(out)
	for id in ids:
		var dir := "res://assets/holes/%s/" % id
		var pck := PCKPacker.new()
		var path := out.path_join("hole_%s.pck" % id)
		pck.pck_start(path)
		var count := 0
		for f in DirAccess.get_files_at(dir):
			if f.ends_with(".import") or f.get_basename() in SKIP or f in SKIP or f.ends_with(".uid"):
				continue
			var imp := dir + f + ".import"
			if FileAccess.file_exists(imp):
				var cfg := ConfigFile.new()
				cfg.load(imp)
				pck.add_file(imp, ProjectSettings.globalize_path(imp))
				for d in cfg.get_value("deps", "dest_files", []):
					pck.add_file(d, ProjectSettings.globalize_path(d))
					count += 1
			else:
				pck.add_file(dir + f, ProjectSettings.globalize_path(dir + f))
			count += 1
		pck.flush()
		print("%s: %d files, %.1f MB" % [path, count, FileAccess.get_file_as_bytes(path).size() / 1048576.0])
	quit()
