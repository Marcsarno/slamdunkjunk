class_name DialogBox
extends Control
## Bottom-of-screen message. Types out, then waits for a tap or the action key.
##   var d := DialogBox.open(layer, "text"); await d.closed

signal closed

var label := Label.new()
var arrow := Label.new()
var ready_to_close := false


static func open(parent: Node, text: String) -> DialogBox:
	var d := DialogBox.new()
	parent.add_child(d)
	d.show_text(text)
	return d


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	theme = Art.theme()
	var panel := PanelContainer.new()
	panel.position = Vector2(8, 206)
	panel.size = Vector2(464, 58)
	panel.add_theme_stylebox_override("panel", Art.box(Art.PANEL, Art.EDGE, 2, 3, 6))
	add_child(panel)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", 11)
	label.custom_minimum_size = Vector2(448, 44)
	panel.add_child(label)
	arrow.text = "v"
	arrow.add_theme_color_override("font_color", Art.BLAZE)
	arrow.position = Vector2(458, 250)
	arrow.visible = false
	add_child(arrow)


func show_text(text: String) -> void:
	label.text = text
	label.visible_ratio = 0.0
	ready_to_close = false
	var tw := create_tween()
	tw.tween_property(label, "visible_ratio", 1.0, clampf(text.length() * 0.018, 0.15, 1.2))
	tw.tween_callback(func():
		ready_to_close = true
		arrow.visible = true)


func _advance() -> void:
	if not ready_to_close:
		label.visible_ratio = 1.0
		ready_to_close = true
		arrow.visible = true
		return
	closed.emit()
	queue_free()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		_advance()
		accept_event()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("action") or event.is_action_pressed("ui_accept"):
		_advance()
		get_viewport().set_input_as_handled()


func _process(_d: float) -> void:
	if arrow.visible:
		arrow.modulate.a = 1.0 if int(Time.get_ticks_msec() / 400) % 2 == 0 else 0.3
