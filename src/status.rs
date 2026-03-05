//! Status effects that can be applied to players and enemies.

/// A timed status effect.
#[derive(Clone, Debug)]
pub enum StatusKind {
    /// Damage per turn for N turns
    Poison { damage: i32 },
    /// Heal per turn for N turns
    Regen { heal: i32 },
    /// Player gets extra actions (enemy_turn skipped on even ticks)
    Haste,
    /// Player movement is randomized
    Confused,
    /// Entire map revealed
    Revealed,
}

/// An active status effect with remaining duration.
#[derive(Clone, Debug)]
pub struct StatusInstance {
    pub kind: StatusKind,
    pub turns_left: i32,
}

impl StatusInstance {
    pub fn new(kind: StatusKind, turns: i32) -> Self {
        Self { kind, turns_left: turns }
    }

    pub fn label(&self) -> &'static str {
        match self.kind {
            StatusKind::Poison { .. } => "☠Psn",
            StatusKind::Regen { .. } => "♥Rgn",
            StatusKind::Haste => "⚡Hst",
            StatusKind::Confused => "?Cnf",
            StatusKind::Revealed => "👁Map",
        }
    }

    pub fn color(&self) -> &'static str {
        match self.kind {
            StatusKind::Poison { .. } => "#88ff44",
            StatusKind::Regen { .. } => "#ff88cc",
            StatusKind::Haste => "#ffff44",
            StatusKind::Confused => "#cc44ff",
            StatusKind::Revealed => "#44ccff",
        }
    }
}

/// Tick all statuses on a list, applying effects. Returns (total_damage, total_heal).
/// Removes expired effects.
pub fn tick_statuses(statuses: &mut Vec<StatusInstance>) -> (i32, i32) {
    let mut damage = 0;
    let mut heal = 0;
    for s in statuses.iter_mut() {
        match s.kind {
            StatusKind::Poison { damage: d } => damage += d,
            StatusKind::Regen { heal: h } => heal += h,
            _ => {}
        }
        s.turns_left -= 1;
    }
    statuses.retain(|s| s.turns_left > 0);
    (damage, heal)
}

/// Check if a specific status kind is active.
pub fn has_status(statuses: &[StatusInstance], check: &str) -> bool {
    statuses.iter().any(|s| s.label().contains(check))
}

pub fn has_haste(statuses: &[StatusInstance]) -> bool {
    statuses.iter().any(|s| matches!(s.kind, StatusKind::Haste))
}

pub fn has_confused(statuses: &[StatusInstance]) -> bool {
    statuses.iter().any(|s| matches!(s.kind, StatusKind::Confused))
}

pub fn has_revealed(statuses: &[StatusInstance]) -> bool {
    statuses.iter().any(|s| matches!(s.kind, StatusKind::Revealed))
}
