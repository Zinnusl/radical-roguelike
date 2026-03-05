//! Main game state and loop.

use std::cell::RefCell;
use std::rc::Rc;
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;
use web_sys::{window, HtmlCanvasElement, KeyboardEvent};

use crate::dungeon::{compute_fov, DungeonLevel};
use crate::player::Player;
use crate::render::Renderer;

const MAP_W: i32 = 48;
const MAP_H: i32 = 48;
const FOV_RADIUS: i32 = 8;

struct GameState {
    level: DungeonLevel,
    player: Player,
    renderer: Renderer,
    floor_num: i32,
    seed: u64,
}

impl GameState {
    fn new_floor(&mut self) {
        self.floor_num += 1;
        self.seed = self.seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        self.level = DungeonLevel::generate(MAP_W, MAP_H, self.seed);
        let (sx, sy) = self.level.start_pos();
        self.player.move_to(sx, sy);
        let (px, py) = (self.player.x, self.player.y);
        compute_fov(&mut self.level, px, py, FOV_RADIUS);
    }

    fn try_move(&mut self, dx: i32, dy: i32) {
        let (nx, ny) = self.player.intended_move(dx, dy);
        if !self.level.is_walkable(nx, ny) {
            return;
        }
        // Check for stairs
        let tile = self.level.tile(nx, ny);
        self.player.move_to(nx, ny);

        if tile == crate::dungeon::Tile::StairsDown {
            self.new_floor();
            return;
        }

        let (px, py) = (self.player.x, self.player.y);
        compute_fov(&mut self.level, px, py, FOV_RADIUS);
    }

    fn render(&self) {
        self.renderer
            .draw(&self.level, &self.player, self.floor_num);
    }
}

pub fn init_game() -> Result<(), JsValue> {
    let win = window().ok_or("no window")?;
    let doc = win.document().ok_or("no document")?;

    // Create canvas
    let canvas: HtmlCanvasElement = doc.create_element("canvas")?.dyn_into()?;
    canvas.set_id("game-canvas");
    canvas.set_width(800);
    canvas.set_height(600);
    canvas.set_attribute(
        "style",
        "display:block; margin:0 auto; background:#0d0b14; image-rendering:pixelated;",
    )?;
    doc.body().unwrap().append_child(&canvas)?;

    // Remove loading indicator
    if let Some(el) = doc.get_element_by_id("loading") {
        el.remove();
    }

    let renderer = Renderer::new(canvas).map_err(|e| JsValue::from_str(e))?;

    // Initial seed from performance.now()
    let seed = win.performance().map(|p| p.now() as u64).unwrap_or(42);
    let level = DungeonLevel::generate(MAP_W, MAP_H, seed);
    let (sx, sy) = level.start_pos();
    let player = Player::new(sx, sy);

    let state = Rc::new(RefCell::new(GameState {
        level,
        player,
        renderer,
        floor_num: 1,
        seed,
    }));

    // Initial FOV
    {
        let mut s = state.borrow_mut();
        let (px, py) = (s.player.x, s.player.y);
        compute_fov(&mut s.level, px, py, FOV_RADIUS);
    }

    // Keyboard input
    {
        let state = Rc::clone(&state);
        let closure = Closure::<dyn FnMut(KeyboardEvent)>::new(move |event: KeyboardEvent| {
            let key = event.key();
            let (dx, dy) = match key.as_str() {
                "ArrowUp" | "w" | "W" => (0, -1),
                "ArrowDown" | "s" | "S" => (0, 1),
                "ArrowLeft" | "a" | "A" => (-1, 0),
                "ArrowRight" | "d" | "D" => (1, 0),
                _ => return,
            };
            event.prevent_default();
            let mut s = state.borrow_mut();
            s.try_move(dx, dy);
            s.render();
        });
        doc.add_event_listener_with_callback("keydown", closure.as_ref().unchecked_ref())?;
        closure.forget();
    }

    // Initial render
    state.borrow().render();

    Ok(())
}
