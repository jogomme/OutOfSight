from time import perf_counter

import pico2d as canvas


def run(scene, width, height):
    canvas.open_canvas(width, height, sync=True)
    previous = perf_counter()
    try:
        while True:
            for event in canvas.get_events():
                if event.type == canvas.SDL_QUIT:
                    return
                scene.handle_event(event)

            now = perf_counter()
            scene.update(min(now - previous, 0.05))
            previous = now
            canvas.clear_canvas()
            scene.draw()
            canvas.update_canvas()
    finally:
        canvas.close_canvas()
