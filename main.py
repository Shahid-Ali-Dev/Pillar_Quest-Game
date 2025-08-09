
import pygame
import sys
import random
import math
import json
from pathlib import Path

# ------------------------ CONFIG ------------------------
WIDTH, HEIGHT = 960, 640
FPS = 60
TILE = 48
GRAVITY = 0.8
FONT_NAME = None
ASSET_DIR = Path("assets")
SAVE_FILE = Path("save_data.json")

# Player tuning (reachable pillar tuning)
PLAYER_SPEED = 6
PLAYER_JUMP_POWER = -15
DOUBLE_JUMP_MULT = 0.95

# Jump helpers
COYOTE_TIME = 8      # frames allowed after leaving ground to still jump
JUMP_BUFFER = 8      # frames the jump press is buffered

# Difficulty per level
DIFFICULTY = {
    1: {"enemy_count": 4, "enemy_speed": 1.0},
    2: {"enemy_count": 6, "enemy_speed": 1.2},
    3: {"enemy_count": 8, "enemy_speed": 1.5},
    4: {"enemy_count": 10, "enemy_speed": 1.9},
    5: {"enemy_count": 12, "enemy_speed": 2.3},
}
MAX_LEVEL = 6

# ------------------------ UTIL ------------------------

def load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

# ------------------------ PYGAME SETUP ------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
if FONT_NAME:
    font = pygame.font.Font(FONT_NAME, 20)
else:
    font = pygame.font.SysFont('consolas', 18)
big_font = pygame.font.SysFont('consolas', 48)

# ------------------------ SPRITES / HELPERS ------------------------
class Camera:
    def __init__(self, width, height):
        self.rect = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
    def apply(self, target):
        return target.rect.move(-self.rect.x, -self.rect.y)
    def update(self, target):
        x = target.rect.centerx - WIDTH // 2
        y = target.rect.centery - HEIGHT // 2
        x = max(0, min(x, self.width - WIDTH))
        y = max(0, min(y, self.height - HEIGHT))
        self.rect.topleft = (x, y)

class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, vel, lifespan=40):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.lifespan = lifespan
        self.image = pygame.Surface((4,4), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255,200,80), (2,2), 2)
        self.rect = self.image.get_rect(center=pos)
    def update(self):
        self.vel.y += 0.3
        self.pos += self.vel
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.lifespan -= 1
        if self.lifespan <= 0:
            self.kill()

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill((40,40,40))
        self.rect = self.image.get_rect(topleft=(x, y))

class Checkpoint(pygame.sprite.Sprite):
    def __init__(self, platform: Platform):
        super().__init__()
        # create a small flag graphic (pole + flag)
        self.image = pygame.Surface((20, 28), pygame.SRCALPHA)
        pole_rect = pygame.Rect(8, 0, 4, 28)
        pygame.draw.rect(self.image, (120,120,120), pole_rect)
        # flag
        pygame.draw.polygon(self.image, (200,30,30), [(12,6),(20,10),(12,14)])
        self.rect = self.image.get_rect(midbottom=(platform.rect.centerx, platform.rect.top))
        self.activated = False
        # respawn slightly above the platform top
        self.respawn_point = (self.rect.centerx, self.rect.top)

    def activate(self):
        self.activated = True
        # visual: change flag color when activated
        self.image.fill((0,0,0,0))
        pole_rect = pygame.Rect(8, 0, 4, 28)
        pygame.draw.rect(self.image, (120,120,120), pole_rect)
        pygame.draw.polygon(self.image, (30,200,80), [(12,6),(20,10),(12,14)])

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((34,46))
        self.image.fill((60,150,200))
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.vel = pygame.Vector2(0,0)
        self.speed = PLAYER_SPEED
        self.jump_power = PLAYER_JUMP_POWER
        self.on_ground = False
        self.double_jump = True
        self.dash_cooldown = 0
        self.facing = 1
        self.lives = 3
        self.score = 0
        # jumping helpers
        self.coyote_timer = 0
        self.jump_buffer = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self.jump_buffer = JUMP_BUFFER

    def update(self, platforms, bullets_group, particles):
        prev_on_ground = self.on_ground
        self.on_ground = False

        keys = pygame.key.get_pressed()
        self.vel.x = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vel.x = -self.speed
            self.facing = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vel.x = self.speed
            self.facing = 1

        # dash
        if keys[pygame.K_LSHIFT] and self.dash_cooldown<=0:
            self.vel.x = 18 * self.facing
            self.dash_cooldown = 45
            for i in range(12):
                particles.add(Particle(self.rect.center, (random.uniform(-3,3), random.uniform(-2,2))))
        if self.dash_cooldown>0:
            self.dash_cooldown -= 1

        # jump buffering + coyote + double jump
        if self.jump_buffer > 0:
            if prev_on_ground or self.coyote_timer > 0:
                self.vel.y = self.jump_power
                self.on_ground = False
                self.double_jump = True
                self.jump_buffer = 0
            elif self.double_jump:
                self.vel.y = self.jump_power * DOUBLE_JUMP_MULT
                self.double_jump = False
                self.jump_buffer = 0
                for i in range(6):
                    particles.add(Particle(self.rect.midbottom, (random.uniform(-2,2), random.uniform(-6,-1))))
        if self.jump_buffer>0:
            self.jump_buffer -= 1

        # physics
        self.vel.y += GRAVITY
        self.rect.x += round(self.vel.x)
        self.collide(platforms, 'x')
        self.rect.y += round(self.vel.y)
        self.collide(platforms, 'y')

        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
            self.double_jump = True
        else:
            if self.coyote_timer > 0:
                self.coyote_timer -= 1

        # shooting
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            bx = self.rect.centerx
            by = self.rect.centery
            dx = mx + camera.rect.x - bx
            dy = my + camera.rect.y - by
            if len(bullets_group) < 6:
                angle = math.atan2(dy, dx)
                bullets_group.add(Bullet((bx,by), angle, 12, owner='player'))

        # falling death
        if self.rect.top > LEVEL_HEIGHT + 200:
            self.lives -= 1
            return 'died'
        return None

    def collide(self, platforms, dir):
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for p in hits:
            if dir == 'x':
                if self.vel.x > 0:
                    self.rect.right = p.rect.left
                elif self.vel.x < 0:
                    self.rect.left = p.rect.right
                self.vel.x = 0
            if dir == 'y':
                if self.vel.y > 0:
                    self.rect.bottom = p.rect.top
                    self.on_ground = True
                    self.vel.y = 0
                elif self.vel.y < 0:
                    self.rect.top = p.rect.bottom
                    self.vel.y = 0

    def respawn(self, point):
        # point is (midbottom_x, midbottom_y)
        self.rect.midbottom = (point[0], point[1])
        self.vel = pygame.Vector2(0,0)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, angle, speed, owner='enemy'):
        super().__init__()
        self.image = pygame.Surface((8,8), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 80, 80) if owner=='enemy' else (80,255,120), (4,4), 4)
        self.rect = self.image.get_rect(center=pos)
        self.vel = pygame.Vector2(math.cos(angle)*speed, math.sin(angle)*speed)
        self.owner = owner
    def update(self):
        self.rect.x += round(self.vel.x)
        self.rect.y += round(self.vel.y)
        if self.rect.right < 0 or self.rect.left > LEVEL_WIDTH or self.rect.top > LEVEL_HEIGHT or self.rect.bottom < 0:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, etype='patrol', speed=1):
        super().__init__()
        self.image = pygame.Surface((36,40))
        self.image.fill((200,60,60))
        self.rect = self.image.get_rect(midbottom=(x,y))
        self.type = etype
        self.speed = speed
        self.dir = random.choice([-1,1])
        self.aggro = False
        self.shoot_timer = random.randint(30,120)
        self.vel_y = 0

    def update(self, platforms, player, bullets_group, particles):
        if self.type in ('patrol','chaser'):
            feet_x = self.rect.centerx + self.dir * (self.rect.width//2 + 6)
            ahead_rect = pygame.Rect(feet_x - 4, self.rect.bottom, 8, 8)
            ground_hit = any(p.rect.colliderect(ahead_rect) for p in platforms)
            proposed_rect = self.rect.copy()
            proposed_rect.x += round(self.speed * self.dir)
            wall_hit = any(p.rect.colliderect(proposed_rect) for p in platforms)
            if not ground_hit or wall_hit:
                self.dir *= -1
            else:
                if self.type == 'patrol':
                    self.rect.x += round(self.speed * self.dir)
                elif self.type == 'chaser':
                    if abs(player.rect.centerx - self.rect.centerx) < 400:
                        self.aggro = True
                    if self.aggro:
                        if player.rect.centerx < self.rect.centerx:
                            self.rect.x -= round(self.speed)
                            self.dir = -1
                        else:
                            self.rect.x += round(self.speed)
                            self.dir = 1
        elif self.type == 'shooter':
            self.shoot_timer -= 1
            if self.shoot_timer <= 0:
                self.shoot_timer = random.randint(40, 120)
                dx = player.rect.centerx - self.rect.centerx
                dy = player.rect.centery - self.rect.centery
                angle = math.atan2(dy, dx)
                bullets_group.add(Bullet(self.rect.center, angle, 6, owner='enemy'))

        # vertical physics
        self.vel_y += GRAVITY
        self.rect.y += round(self.vel_y)
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for p in hits:
            if self.vel_y > 0 and self.rect.bottom > p.rect.top:
                self.rect.bottom = p.rect.top
                self.vel_y = 0
        if random.random() < 0.01:
            particles.add(Particle(self.rect.midbottom, (random.uniform(-1,1), random.uniform(-4,-1))))

# ------------------------ LEVELS (no bridging) ------------------------
# design levels with reachable gaps given PLAYER_SPEED and PLAYER_JUMP_POWER
LEVEL_TEMPLATES = [
    [
        "..................................................",
        "..................................................",
        "..................................................",
        "....................C.............................",
        "..........#####..........#####....................",
        "..................................................",
        "......P...........................................",
        "##########......#####.............######..........",
        "..................................................",
        "..................................................",
    ],
    [
        "..................................................",
        "....................C.............................",
        "...............#####.............#####............",
        "..................................................",
        "......P.....E......#####.....E....................",
        "....##########....................###########....",
        "..................................................",
        "..................#####......................E...",
        "..................................................",
        "..................................................",
    ],
    [
        "..................................................",
        "....................................C.............",
        "..........#####..............####...............E",
        "..................................................",
        "........P...........#####.........................",
        "....##########....................######..........",
        ".............................E....................",
        "....................#####.........................",
        "..................................................",
        "..................................................",
    ],
]

# build level - returns platforms, enemies, collectibles, player_spawn, checkpoints_group, width, height

def build_level_from_template(template):
    rows = len(template)
    cols = len(template[0])
    level_w = cols * TILE
    level_h = rows * TILE
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    collectibles = pygame.sprite.Group()
    checkpoints = pygame.sprite.Group()
    player_spawn = (TILE*2, TILE*6)

    for r, row in enumerate(template):
        for c, ch in enumerate(row):
            x = c * TILE
            y = r * TILE
            if ch == '#':
                platforms.add(Platform(x, y, TILE, TILE))
            elif ch == 'P':
                player_spawn = (x + TILE//2, y + TILE)
            elif ch == 'E':
                etype = random.choice(['patrol','chaser','shooter'])
                enemies.add(Enemy(x+TILE//2, y+TILE, etype=etype, speed=random.uniform(0.8,1.6)))
            elif ch == 'C':
                c_surf = pygame.Surface((20,20))
                c_surf.fill((255,215,0))
                spr = pygame.sprite.Sprite()
                spr.image = c_surf
                spr.rect = c_surf.get_rect(center=(x+TILE//2, y+TILE//2))
                collectibles.add(spr)

    # Create checkpoint flag on the rightmost platform (last pillar)
    if len(platforms) > 0:
        rightmost = max(platforms, key=lambda p: (p.rect.left, -p.rect.top))
        cp = Checkpoint(rightmost)
        checkpoints.add(cp)

    return platforms, enemies, collectibles, player_spawn, checkpoints, level_w, level_h

# ------------------------ LEVEL MANAGER ------------------------
class LevelManager:
    def __init__(self):
        self.current = 1
    def load_level(self, n):
        template = LEVEL_TEMPLATES[(n-1) % len(LEVEL_TEMPLATES)]
        platforms, enemies, collectibles, spawn, checkpoints, lw, lh = build_level_from_template(template)
        settings = DIFFICULTY.get(min(n, max(DIFFICULTY.keys())), DIFFICULTY[max(DIFFICULTY.keys())])
        # spawn extra enemies per difficulty
        for _ in range(settings['enemy_count'] - len(enemies)):
            x = random.randint(2, max(3, (lw//TILE)-3)) * TILE
            y = random.randint(1, max(2, (lh//TILE)-2)) * TILE
            enemies.add(Enemy(x, y, etype=random.choice(['patrol','chaser']), speed=settings['enemy_speed']))
        return {
            'platforms': platforms,
            'enemies': enemies,
            'collectibles': collectibles,
            'spawn': spawn,
            'checkpoints': checkpoints,
            'width': lw,
            'height': lh,
            'settings': settings
        }

# ------------------------ GLOBAL PLACEHOLDERS ------------------------
LEVEL_WIDTH = WIDTH * 2
LEVEL_HEIGHT = HEIGHT * 2
camera = Camera(LEVEL_WIDTH, LEVEL_HEIGHT)

# ------------------------ RENDER / HUD ------------------------

def draw_parallax(cam_rect):
    for i in range(3):
        offset = (cam_rect.x*0.2*(i+1)) % WIDTH
        rect = pygame.Rect(-offset, 0, WIDTH*2, HEIGHT)
        surface = pygame.Surface((rect.width, rect.height))
        color = (30 + i*20, 20 + i*10, 40 + i*10)
        surface.fill(color)
        screen.blit(surface, (rect.x, rect.y))


def render_hud(player, level_num, highscore):
    txt = font.render(f"Lives: {player.lives}", True, (255,255,255))
    screen.blit(txt, (8,8))
    txt2 = font.render(f"Score: {player.score}", True, (255,255,255))
    screen.blit(txt2, (8,34))
    lvl = font.render(f"Level: {level_num}", True, (255,255,255))
    screen.blit(lvl, (WIDTH-150, 8))
    hs = font.render(f"Highscore: {highscore}", True, (255,255,255))
    screen.blit(hs, (WIDTH-300, 34))

# ------------------------ GAME LOOP (refactored restart) ------------------------

def run_game():
    global LEVEL_WIDTH, LEVEL_HEIGHT, camera
    save = load_json(SAVE_FILE, default={'highscore':0})
    highscore = save.get('highscore', 0)
    level_manager = LevelManager()
    level_data = level_manager.load_level(1)

    LEVEL_WIDTH = level_data['width']
    LEVEL_HEIGHT = level_data['height']
    camera = Camera(LEVEL_WIDTH, LEVEL_HEIGHT)

    platforms = level_data['platforms']
    enemies = level_data['enemies']
    collectibles = level_data['collectibles']
    checkpoints = level_data['checkpoints']
    player_spawn = level_data['spawn']

    player = Player(*player_spawn)
    bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()
    particles = pygame.sprite.Group()

    level_num = 1
    paused = False
    game_over = False
    win = False
    level_clear_cool = 0
    level_transition_timer = 0
    respawn_point = player_spawn

    while True:
        dt = clock.tick(FPS)
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                # save
                if player.score > highscore:
                    save['highscore'] = player.score
                    save_json(SAVE_FILE, save)
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and not game_over and not win and level_transition_timer==0:
                    paused = not paused
                if event.key == pygame.K_r:
                    return True  # restart requested
        if paused or game_over or win or level_transition_timer>0:
            draw_parallax(camera.rect)
            if level_transition_timer>0:
                text = big_font.render('LEVEL COMPLETE', True, (255,255,255))
            else:
                text = big_font.render('PAUSED' if paused else ('YOU WIN!' if win else 'GAME OVER'), True, (255,255,255))
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
            sub = font.render('P to resume | R to restart | Close window to save and quit', True, (255,255,255))
            screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 60))
            pygame.display.flip()
            # if level_transition_timer running, count down
            if level_transition_timer>0:
                level_transition_timer -= 1
                if level_transition_timer <= 0:
                    # advance to next level
                    level_num += 1
                    if level_num > MAX_LEVEL:
                        win = True
                    else:
                        # load next level
                        level_data = level_manager.load_level(level_num)
                        LEVEL_WIDTH = level_data['width']
                        LEVEL_HEIGHT = level_data['height']
                        camera = Camera(LEVEL_WIDTH, LEVEL_HEIGHT)
                        platforms = level_data['platforms']
                        enemies = level_data['enemies']
                        collectibles = level_data['collectibles']
                        checkpoints = level_data['checkpoints']
                        player_spawn = level_data['spawn']
                        respawn_point = player_spawn
                        player.respawn(respawn_point)
                        player.lives = max(1, player.lives)  # keep at least 1 life
                        player.score += 500 * level_num
            continue

        # pass events for jump buffering
        player.handle_events(events)

        # update
        outcome = player.update(platforms, bullets, particles)
        if outcome == 'died':
            # respawn at current respawn point
            player.respawn(respawn_point)
            # if no lives left, mark game_over
            if player.lives <= 0:
                game_over = True

        bullets.update()
        particles.update()
        for e in list(enemies):
            e.update(platforms, player, enemy_bullets, particles)
        enemy_bullets.update()

        # bullet collisions
        for b in list(bullets):
            hit = pygame.sprite.spritecollideany(b, enemies)
            if hit:
                b.kill()
                hit.kill()
                player.score += 100
                for i in range(10):
                    particles.add(Particle(hit.rect.center, (random.uniform(-3,3), random.uniform(-6,2))))
        for b in list(enemy_bullets):
            if player.rect.colliderect(b.rect):
                b.kill()
                player.lives -= 1
                for i in range(12):
                    particles.add(Particle(player.rect.center, (random.uniform(-4,4), random.uniform(-6,-1))))
                if player.lives <= 0:
                    game_over = True

        # touch enemy
        if pygame.sprite.spritecollideany(player, enemies):
            player.lives -= 1
            player.rect.x -= 60
            for i in range(8):
                particles.add(Particle(player.rect.center, (random.uniform(-3,3), random.uniform(-6,-1))))
            if player.lives <= 0:
                game_over = True

        # collect collectibles
        for c in list(collectibles):
            if player.rect.colliderect(c.rect):
                c.kill()
                player.score += 50
                for i in range(6):
                    particles.add(Particle(c.rect.center, (random.uniform(-2,2), random.uniform(-6,-1))))

        # checkpoint interaction: touch flag -> activate, set respawn and trigger level_transition
        for cp in list(checkpoints):
            if player.rect.colliderect(cp.rect):
                if not cp.activated:
                    cp.activate()
                    respawn_point = cp.respawn_point
                    # play particles
                    for i in range(16):
                        particles.add(Particle(cp.rect.center, (random.uniform(-4,4), random.uniform(-6,-1))))
                    # start short transition timer (frames)
                    level_transition_timer = int(FPS * 0.9)

        # level clear fallback: if enemies and collectibles cleared, auto-advance (same as before)
        if len(enemies) == 0 and len(collectibles) == 0 and level_transition_timer==0:
            level_clear_cool += 1
            if level_clear_cool > FPS*1.2:
                level_transition_timer = int(FPS * 0.9)
                level_clear_cool = 0
        else:
            if not (len(enemies) == 0 and len(collectibles) == 0):
                level_clear_cool = 0

        # camera
        camera.update(player)

        # draw
        draw_parallax(camera.rect)
        for p in platforms:
            screen.blit(p.image, camera.apply(p))
        for c in collectibles:
            screen.blit(c.image, camera.apply(c))
        for e in enemies:
            screen.blit(e.image, camera.apply(e))
        for b in bullets:
            screen.blit(b.image, camera.apply(b))
        for b in enemy_bullets:
            screen.blit(b.image, camera.apply(b))
        screen.blit(player.image, camera.apply(player))
        for cp in checkpoints:
            screen.blit(cp.image, camera.apply(cp))
        for p in particles:
            screen.blit(p.image, camera.apply(p))
        render_hud(player, level_num, highscore)

        pygame.display.flip()

# ------------------------ ENTRYPOINT ------------------------
if __name__ == '__main__':
    try:
        while True:
            restart = run_game()
            if not restart:
                break
    except Exception as e:
        print('Error:', e)
        pygame.quit()
        raise
