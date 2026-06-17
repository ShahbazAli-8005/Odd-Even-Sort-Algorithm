import os
import sys
import csv
import math
import time
import struct
import random
import pygame

# Initialize Pygame Font
pygame.font.init()

# ==========================================
# DESIGN CONSTANTS & PALETTE
# ==========================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors (cyberpunk space-nebula palette)
COLOR_BG = (11, 15, 25)              # Deep space dark blue
COLOR_PANEL_FILL = (22, 27, 34, 180) # Semi-transparent dark grey-blue
COLOR_PANEL_BORDER = (48, 54, 61)   # Muted panel border
COLOR_TEXT = (201, 209, 217)          # Bright off-white
COLOR_TEXT_MUTED = (139, 148, 158)   # Muted grey
COLOR_HIGHLIGHT = (255, 235, 59)      # Comparison (Yellow)
COLOR_ACTION = (255, 69, 58)          # Swaps/Writes (Coral Red)
COLOR_SELECT = (0, 240, 255)          # Insertion Select (Cyan)
COLOR_SUCCESS = (57, 255, 20)         # Sorted Wave (Neon Green)
COLOR_BAR_DEFAULT = (75, 85, 99)       # Neutral unsorted bar
COLOR_BAR_WHITE = (230, 230, 235)      # Alternating white bar
COLOR_BAR_BLACK = (40, 42, 46)         # Alternating black bar

# Vibrant Neon Palette for Concurrency Phases
RUN_COLORS = [
    (0, 200, 255),    # Neon Cyan
    (189, 0, 255),    # Neon Purple
    (57, 255, 20),    # Neon Green
    (255, 0, 127),    # Neon Pink
    (255, 170, 0),    # Neon Orange
    (0, 102, 255)     # Neon Deep Blue
]

# Phase indicators
COLOR_ODD_HIGHLIGHT = (189, 0, 255)   # Purple
COLOR_EVEN_HIGHLIGHT = (0, 200, 255)  # Cyan

# Layout Panels
HEADER_RECT = pygame.Rect(20, 20, 1240, 80)
GRAPH_RECT = pygame.Rect(20, 120, 240, 200)       # Retained only to avoid breaking complexity graph draw method if called
LOG_RECT = pygame.Rect(20, 330, 240, 210)         # Retained only to avoid breaking log draw method if called
CANVAS_RECT = pygame.Rect(20, 250, 1240, 270)     # Main array canvas
BUTTONS_RECT = pygame.Rect(20, 535, 1240, 55)     # Control buttons panel
DETAILS_RECT = pygame.Rect(20, 605, 1240, 95)     # Bottom status and scrubber slider


# ==========================================
# PCM SINE WAVE AUDIO SYNTHESIZER
# ==========================================
def make_sound(frequency, duration, volume=0.08, sample_rate=44100):
    """Synthesizes mono 16-bit PCM sine wave Sound object in memory."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=sample_rate, size=-16, channels=1)
        num_samples = int(sample_rate * duration)
        max_amplitude = 32767 * volume
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            val = int(max_amplitude * math.sin(2 * math.pi * frequency * t))
            samples.append(struct.pack('<h', val))
        byte_data = b''.join(samples)
        return pygame.mixer.Sound(buffer=byte_data)
    except Exception as e:
        print(f"Sound generation failed for frequency {frequency}: {e}")
        return None

class SoundEffects:
    _compare_snd = None
    _swap_snd = None
    _noswap_snd = None
    _complete_snd = None
    _phase_snd = None
    _enabled = True
    
    @classmethod
    def init(cls):
        cls._compare_snd = make_sound(440, 0.04, volume=0.03) # A4 beep
        cls._swap_snd = make_sound(660, 0.06, volume=0.05)    # E5 beep
        cls._noswap_snd = make_sound(330, 0.03, volume=0.02)  # E4 soft click
        cls._complete_snd = make_sound(880, 0.25, volume=0.06) # A5 complete sweep
        cls._phase_snd = make_sound(554, 0.12, volume=0.03)   # C#5 phase transition
        
    @classmethod
    def toggle(cls):
        cls._enabled = not cls._enabled
        return cls._enabled

    @classmethod
    def play_compare(cls):
        if cls._enabled and cls._compare_snd:
            cls._compare_snd.play()

    @classmethod
    def play_swap(cls):
        if cls._enabled and cls._swap_snd:
            cls._swap_snd.play()

    @classmethod
    def play_noswap(cls):
        if cls._enabled and cls._noswap_snd:
            cls._noswap_snd.play()

    @classmethod
    def play_complete(cls):
        if cls._enabled and cls._complete_snd:
            cls._complete_snd.play()

    @classmethod
    def play_phase(cls):
        if cls._enabled and cls._phase_snd:
            cls._phase_snd.play()


# ==========================================
# SORT ITEM COMPARATOR CLASS
# ==========================================
class SortItem:
    """Wraps an array element with a unique ID for stable visual rendering and comparison tracking."""
    def __init__(self, item_id, value, is_placeholder=False):
        self.id = item_id
        self.value = value
        self.is_placeholder = is_placeholder

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)


# ==========================================
# ALGORITHM SNAPSHOT STATE GENERATORS
# ==========================================
def oddeven_seq_generator(arr):
    n = len(arr)
    comps = 0
    swaps = 0
    cycle = 0
    
    yield {
        'arr': list(arr),
        'active': [],
        'type': 'info',
        'desc': f"Odd-Even Sort Started. Array size: {n}. Mode: Sequential.",
        'phase': 'IDLE',
        'cycle': 0,
        'comps': 0,
        'swaps': 0
    }
    
    is_sorted = False
    while not is_sorted:
        is_sorted = True
        cycle += 1
        
        # --- ODD PHASE ---
        yield {
            'arr': list(arr),
            'active': [],
            'type': 'phase_start',
            'desc': f"Cycle {cycle}: Starting ODD Phase (Comparing index pairs 1-2, 3-4, 5-6...).",
            'phase': 'ODD',
            'cycle': cycle,
            'comps': comps,
            'swaps': swaps
        }
        
        swaps_in_odd = 0
        for i in range(1, n - 1, 2):
            comps += 1
            yield {
                'arr': list(arr),
                'active': [i, i+1],
                'type': 'compare',
                'desc': f"ODD Phase: Comparing index {i} ({arr[i].value}) and index {i+1} ({arr[i+1].value}).",
                'phase': 'ODD',
                'cycle': cycle,
                'comps': comps,
                'swaps': swaps
            }
            
            if arr[i].value > arr[i+1].value:
                arr[i], arr[i+1] = arr[i+1], arr[i]
                swaps += 1
                swaps_in_odd += 1
                is_sorted = False
                yield {
                    'arr': list(arr),
                    'active': [i, i+1],
                    'type': 'swap',
                    'desc': f"ODD Phase: Swap performed because {arr[i+1].value} > {arr[i].value}.",
                    'phase': 'ODD',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
            else:
                yield {
                    'arr': list(arr),
                    'active': [i, i+1],
                    'type': 'no_swap',
                    'desc': f"ODD Phase: Already in correct order ({arr[i].value} <= {arr[i+1].value}).",
                    'phase': 'ODD',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
                
        # --- EVEN PHASE ---
        yield {
            'arr': list(arr),
            'active': [],
            'type': 'phase_start',
            'desc': f"Cycle {cycle}: Starting EVEN Phase (Comparing index pairs 0-1, 2-3, 4-5...).",
            'phase': 'EVEN',
            'cycle': cycle,
            'comps': comps,
            'swaps': swaps
        }
        
        swaps_in_even = 0
        for i in range(0, n - 1, 2):
            comps += 1
            yield {
                'arr': list(arr),
                'active': [i, i+1],
                'type': 'compare',
                'desc': f"EVEN Phase: Comparing index {i} ({arr[i].value}) and index {i+1} ({arr[i+1].value}).",
                'phase': 'EVEN',
                'cycle': cycle,
                'comps': comps,
                'swaps': swaps
            }
            
            if arr[i].value > arr[i+1].value:
                arr[i], arr[i+1] = arr[i+1], arr[i]
                swaps += 1
                swaps_in_even += 1
                is_sorted = False
                yield {
                    'arr': list(arr),
                    'active': [i, i+1],
                    'type': 'swap',
                    'desc': f"EVEN Phase: Swap performed because {arr[i+1].value} > {arr[i].value}.",
                    'phase': 'EVEN',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
            else:
                yield {
                    'arr': list(arr),
                    'active': [i, i+1],
                    'type': 'no_swap',
                    'desc': f"EVEN Phase: Already in correct order ({arr[i].value} <= {arr[i+1].value}).",
                    'phase': 'EVEN',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
                
        yield {
            'arr': list(arr),
            'active': [],
            'type': 'cycle_complete',
            'desc': f"Cycle {cycle} complete. Swaps in cycle: {swaps_in_odd + swaps_in_even}.",
            'phase': 'IDLE',
            'cycle': cycle,
            'comps': comps,
            'swaps': swaps
        }
        
    yield {
        'arr': list(arr),
        'active': [],
        'type': 'done',
        'desc': f"Sorting complete! Total Comparisons: {comps}, Total Swaps: {swaps}. Array is fully sorted.",
        'phase': 'IDLE',
        'cycle': cycle,
        'comps': comps,
        'swaps': swaps
    }


def oddeven_parallel_generator(arr):
    n = len(arr)
    comps = 0
    swaps = 0
    cycle = 0
    
    yield {
        'arr': list(arr),
        'active': [],
        'type': 'info',
        'desc': f"Odd-Even Sort Started. Array size: {n}. Mode: Parallel.",
        'phase': 'IDLE',
        'cycle': 0,
        'comps': 0,
        'swaps': 0
    }
    
    is_sorted = False
    while not is_sorted:
        is_sorted = True
        cycle += 1
        
        # --- ODD PHASE ---
        odd_pairs = [(i, i + 1) for i in range(1, n - 1, 2)]
        swaps_in_odd = 0
        if odd_pairs:
            comps += len(odd_pairs)
            active_compare = []
            for i, j in odd_pairs:
                active_compare.extend([i, j])
                
            yield {
                'arr': list(arr),
                'active': active_compare,
                'type': 'compare_parallel',
                'desc': f"Cycle {cycle} ODD Phase: Parallel Comparison of all odd index pairs ({len(odd_pairs)} pairs).",
                'phase': 'ODD',
                'cycle': cycle,
                'comps': comps,
                'swaps': swaps
            }
            
            swapping_pairs = [pair for pair in odd_pairs if arr[pair[0]].value > arr[pair[1]].value]
            swaps_in_odd = len(swapping_pairs)
            if swapping_pairs:
                active_swap = []
                for i, j in swapping_pairs:
                    active_swap.extend([i, j])
                    arr[i], arr[j] = arr[j], arr[i]
                    swaps += 1
                is_sorted = False
                
                yield {
                    'arr': list(arr),
                    'active': active_swap,
                    'type': 'swap_parallel',
                    'desc': f"Cycle {cycle} ODD Phase: Performing parallel swaps on {len(swapping_pairs)} pairs.",
                    'phase': 'ODD',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
            else:
                yield {
                    'arr': list(arr),
                    'active': active_compare,
                    'type': 'no_swap_parallel',
                    'desc': f"Cycle {cycle} ODD Phase: No swaps required. All pairs in order.",
                    'phase': 'ODD',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
                
        # --- EVEN PHASE ---
        even_pairs = [(i, i + 1) for i in range(0, n - 1, 2)]
        swaps_in_even = 0
        if even_pairs:
            comps += len(even_pairs)
            active_compare = []
            for i, j in even_pairs:
                active_compare.extend([i, j])
                
            yield {
                'arr': list(arr),
                'active': active_compare,
                'type': 'compare_parallel',
                'desc': f"Cycle {cycle} EVEN Phase: Parallel Comparison of all even index pairs ({len(even_pairs)} pairs).",
                'phase': 'EVEN',
                'cycle': cycle,
                'comps': comps,
                'swaps': swaps
            }
            
            swapping_pairs = [pair for pair in even_pairs if arr[pair[0]].value > arr[pair[1]].value]
            swaps_in_even = len(swapping_pairs)
            if swapping_pairs:
                active_swap = []
                for i, j in swapping_pairs:
                    active_swap.extend([i, j])
                    arr[i], arr[j] = arr[j], arr[i]
                    swaps += 1
                is_sorted = False
                
                yield {
                    'arr': list(arr),
                    'active': active_swap,
                    'type': 'swap_parallel',
                    'desc': f"Cycle {cycle} EVEN Phase: Performing parallel swaps on {len(swapping_pairs)} pairs.",
                    'phase': 'EVEN',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
            else:
                yield {
                    'arr': list(arr),
                    'active': active_compare,
                    'type': 'no_swap_parallel',
                    'desc': f"Cycle {cycle} EVEN Phase: No swaps required. All pairs in order.",
                    'phase': 'EVEN',
                    'cycle': cycle,
                    'comps': comps,
                    'swaps': swaps
                }
                
        yield {
            'arr': list(arr),
            'active': [],
            'type': 'cycle_complete',
            'desc': f"Cycle {cycle} complete. Swaps in cycle: {swaps_in_odd + swaps_in_even}.",
            'phase': 'IDLE',
            'cycle': cycle,
            'comps': comps,
            'swaps': swaps
        }
        
        if is_sorted:
            break
            
    yield {
        'arr': list(arr),
        'active': [],
        'type': 'done',
        'desc': f"Sorting complete! Total Comparisons: {comps}, Total Swaps: {swaps}. Array is fully sorted.",
        'phase': 'IDLE',
        'cycle': cycle,
        'comps': comps,
        'swaps': swaps
    }


# ==========================================
# BAR ELEMENT DESIGN REPRESENTATION
# ==========================================
class Bar:
    """Represents a capsule bar inside the visualizer, tracking smooth sliding positions and neon colors."""
    def __init__(self, sort_item, target_index, max_val, total_elements):
        self.value = sort_item.value if hasattr(sort_item, 'value') else sort_item
        self.id = sort_item.id if hasattr(sort_item, 'id') else None
        self.is_placeholder = getattr(sort_item, 'is_placeholder', False)
        
        self.target_index = target_index
        self.max_val = max_val
        self.total_elements = total_elements
        
        self.current_x = 0.0
        self.target_x = 0.0
        self.current_y = 0.0
        self.target_y = 0.0
        self.height = 0.0
        
        self.color = COLOR_BAR_DEFAULT
        self.target_color = COLOR_BAR_DEFAULT
        
        self.update_dimensions(target_index)
        self.current_x = self.target_x
        self.current_y = self.target_y

    def update_dimensions(self, index):
        self.target_index = index
        canvas_x = CANVAS_RECT.x
        canvas_y = CANVAS_RECT.y
        canvas_w = CANVAS_RECT.width
        canvas_h = CANVAS_RECT.height
        
        spacing = 4 if self.total_elements < 20 else (2 if self.total_elements < 40 else 1)
        total_spacings = spacing * (self.total_elements - 1)
        bar_w = (canvas_w - total_spacings) / self.total_elements
        
        self.target_x = canvas_x + index * (bar_w + spacing)
        
        if self.max_val > 0:
            self.height = (self.value / self.max_val) * (canvas_h - 70) + 15
        else:
            self.height = 15
            
        self.target_y = canvas_y + canvas_h - 35 - self.height

    def update(self, dt):
        speed = 0.15
        self.current_x += (self.target_x - self.current_x) * speed
        self.current_y += (self.target_y - self.current_y) * speed
        
        r = self.color[0] + (self.target_color[0] - self.color[0]) * 0.2
        g = self.color[1] + (self.target_color[1] - self.color[1]) * 0.2
        b = self.color[2] + (self.target_color[2] - self.color[2]) * 0.2
        self.color = (int(r), int(g), int(b))

    def draw(self, surface, bar_w, font_val, font_idx, is_active=False):
        r_top = max(4, min(12, int(bar_w // 2)))
        
        if self.is_placeholder:
            pygame.draw.rect(surface, (33, 38, 45), (self.current_x, self.current_y, bar_w, self.height), 2, 
                             border_top_left_radius=r_top, border_top_right_radius=r_top)
            return

        # Active elements glow overlay
        if is_active:
            glow_color = self.color
            for glow_offset in range(1, 6):
                alpha = int(140 / (glow_offset + 1))
                glow_surf = pygame.Surface((int(bar_w + glow_offset * 2), int(self.height + glow_offset * 2)), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, alpha), (0, 0, int(bar_w + glow_offset * 2), int(self.height + glow_offset * 2)), 
                                 border_top_left_radius=r_top + glow_offset, border_top_right_radius=r_top + glow_offset)
                surface.blit(glow_surf, (self.current_x - glow_offset, self.current_y - glow_offset))

        pygame.draw.rect(surface, self.color, (self.current_x, self.current_y, bar_w, self.height), 
                         border_top_left_radius=r_top, border_top_right_radius=r_top)

        # Values displayed at the bottom of the canvas, below the bars
        if bar_w >= 6:
            val_text = font_val.render(str(self.value), True, COLOR_TEXT)
            val_rect = val_text.get_rect(center=(int(self.current_x + bar_w / 2), int(CANVAS_RECT.y + CANVAS_RECT.height - 20)))
            surface.blit(val_text, val_rect)


# ==========================================
# DRIFTING STARS & EXPLODING SPARKS & BUTTONS
# ==========================================
class StarParticle:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.uniform(0.5, 2.5)
        self.speed = random.uniform(2.0, 12.0)
        self.color = (
            random.randint(100, 150),
            random.randint(120, 200),
            random.randint(220, 255),
            random.randint(30, 90)
        )

    def update(self, dt):
        self.y += self.speed * dt * 60
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randint(0, SCREEN_WIDTH)
            self.speed = random.uniform(2.0, 12.0)


class SparkParticle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(-math.pi/6, -5*math.pi/6)
        speed = random.uniform(80.0, 250.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.size = random.uniform(3.0, 7.0)
        self.alpha = 255
        self.decay = random.uniform(400.0, 600.0)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 350.0 * dt
        self.alpha = max(0, int(self.alpha - self.decay * dt))
        self.size = max(1.0, self.size - 3.0 * dt)

    def draw(self, surface):
        if self.alpha <= 0:
            return
        spark_surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(spark_surf, (*self.color, self.alpha), (int(self.size), int(self.size)), int(self.size))
        surface.blit(spark_surf, (self.x - self.size, self.y - self.size))


class Button:
    def __init__(self, rect, text, callback, color=(33, 38, 45), hover_color=(48, 54, 61)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface, font):
        bg_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, 1, border_radius=6)
        text_surf = font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.callback()
                return True
        return False


class CheckmarkAnim:
    def __init__(self, x, y):
        self.cx = x
        self.cy = y
        self.life = 0.5
        self.max_life = 0.5

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, screen):
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        scale = 1.0 + (1.0 - self.life / self.max_life) * 0.3
        
        c_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        color = (57, 255, 20, alpha)
        
        pygame.draw.line(c_surf, color, (10, 20), (18, 28), 3)
        pygame.draw.line(c_surf, color, (18, 28), (30, 12), 3)
        
        sw = int(40 * scale)
        sh = int(40 * scale)
        scaled_surf = pygame.transform.smoothscale(c_surf, (sw, sh))
        
        rect = scaled_surf.get_rect(center=(int(self.cx), int(self.cy)))
        screen.blit(scaled_surf, rect.topleft)


class AnimationManager:
    def __init__(self):
        self.stars = [StarParticle() for _ in range(50)]
        self.sparks = []
        self.checkmarks = []

    def clear(self):
        self.sparks = []
        self.checkmarks = []

    def trigger_sparks(self, x, y, color, count=10):
        for _ in range(count):
            self.sparks.append(SparkParticle(x, y, color))

    def trigger_checkmark(self, x, y):
        self.checkmarks.append(CheckmarkAnim(x, y))

    def update(self, dt):
        for star in self.stars:
            star.update(dt)
        self.sparks = [s for s in self.sparks if s.update(dt)]
        self.checkmarks = [c for c in self.checkmarks if c.update(dt)]

    def draw_bg_stars(self, screen):
        star_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for s in self.stars:
            pygame.draw.circle(star_surf, s.color, (int(s.x), int(s.y)), int(s.size))
        screen.blit(star_surf, (0, 0))

    def draw_effects(self, screen):
        for s in self.sparks:
            s.draw(screen)
        for c in self.checkmarks:
            c.draw(screen)

    def draw_glowing_connection(self, screen, x1, y1, x2, y2, color):
        glow_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.line(glow_surf, (*color, 45), (x1, y1), (x2, y2), 8)
        pygame.draw.line(glow_surf, (*color, 110), (x1, y1), (x2, y2), 4)
        pygame.draw.line(glow_surf, (255, 255, 255, 255), (x1, y1), (x2, y2), 1)
        screen.blit(glow_surf, (0, 0))

    def draw_swap_arrow(self, screen, x1, y_base, x2, color):
        arrow_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        mid_x = (x1 + x2) / 2
        y_max = y_base + 20
        
        points = []
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            px = x1 + t * (x2 - x1)
            py = y_base + 5 + 4 * (y_max - y_base - 5) * t * (1 - t)
            points.append((int(px), int(py)))
            
        if len(points) >= 2:
            pygame.draw.lines(arrow_surf, (*color, 180), False, points, 2)
            self._draw_arrowhead_tip(arrow_surf, points[0][0], points[0][1], math.atan2(points[0][1] - points[1][1], points[0][0] - points[1][0]), color)
            self._draw_arrowhead_tip(arrow_surf, points[-1][0], points[-1][1], math.atan2(points[-1][1] - points[-2][1], points[-1][0] - points[-2][0]), color)
            
        screen.blit(arrow_surf, (0, 0))

    def _draw_arrowhead_tip(self, surf, x, y, angle, color, size=6):
        p1 = (x + size * math.cos(angle - 0.5), y + size * math.sin(angle - 0.5))
        p2 = (x + size * math.cos(angle + 0.5), y + size * math.sin(angle + 0.5))
        pygame.draw.polygon(surf, (*color, 225), [(x, y), p1, p2])


# ==========================================
# REALTIME DYNAMIC COMPLEXITY GRAPH DISPLAY
# ==========================================
class ComplexityGraph:
    def __init__(self):
        pass

    def draw(self, screen, states, current_state_idx, font_small):
        # Draw rounded glass container
        w, h = GRAPH_RECT.width, GRAPH_RECT.height
        panel_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, COLOR_PANEL_FILL, (0, 0, w, h), border_radius=8)
        pygame.draw.rect(panel_surf, COLOR_PANEL_BORDER, (0, 0, w, h), 1, border_radius=8)
        screen.blit(panel_surf, GRAPH_RECT.topleft)

        origin_x = GRAPH_RECT.x + 50
        origin_y = GRAPH_RECT.y + GRAPH_RECT.height - 30
        graph_width = GRAPH_RECT.width - 70
        graph_height = GRAPH_RECT.height - 60

        title_text = font_small.render("ALGORITHM METRICS VS STEPS", True, COLOR_TEXT)
        screen.blit(title_text, (GRAPH_RECT.x + 15, GRAPH_RECT.y + 12))

        if not states or current_state_idx >= len(states):
            return

        curr_state = states[current_state_idx]
        comps_max = curr_state.get('comps', 0)
        swaps_max = curr_state.get('swaps', 0)
        max_y = max(10, comps_max, swaps_max)
        
        total_steps = len(states)
        
        # Grid lines
        num_grid_y = 3
        for i in range(num_grid_y + 1):
            y_val = int(max_y * i / num_grid_y)
            y_pos = origin_y - (i / num_grid_y) * graph_height
            pygame.draw.line(screen, (35, 40, 50), (origin_x, y_pos), (origin_x + graph_width, y_pos), 1)
            
            lbl = font_small.render(str(y_val), True, COLOR_TEXT_MUTED)
            lbl_rect = lbl.get_rect(right=origin_x - 8, centery=y_pos)
            screen.blit(lbl, lbl_rect)

        # Axes
        pygame.draw.line(screen, COLOR_TEXT_MUTED, (origin_x, origin_y), (origin_x + graph_width, origin_y), 2)
        pygame.draw.line(screen, COLOR_TEXT_MUTED, (origin_x, origin_y), (origin_x, origin_y - graph_height), 2)

        if current_state_idx < 1:
            return

        comp_points = []
        swap_points = []

        for k in range(current_state_idx + 1):
            st = states[k]
            c = st.get('comps', 0)
            s = st.get('swaps', 0)
            
            x_pct = k / (total_steps - 1) if total_steps > 1 else 0.0
            y_pct_c = c / max_y
            y_pct_s = s / max_y
            
            px = int(origin_x + x_pct * graph_width)
            py_c = int(origin_y - y_pct_c * graph_height)
            py_s = int(origin_y - y_pct_s * graph_height)
            
            comp_points.append((px, py_c))
            swap_points.append((px, py_s))

        if len(comp_points) >= 2:
            try:
                pygame.draw.lines(screen, COLOR_HIGHLIGHT, False, comp_points, 2)
                pygame.draw.lines(screen, COLOR_ACTION, False, swap_points, 2)
            except Exception:
                for idx in range(len(comp_points) - 1):
                    pygame.draw.line(screen, COLOR_HIGHLIGHT, comp_points[idx], comp_points[idx+1], 2)
                    pygame.draw.line(screen, COLOR_ACTION, swap_points[idx], swap_points[idx+1], 2)


# ==========================================
# HISTORY LOG GLASS PANEL COMPONENT
# ==========================================
class StatisticsPanel:
    def __init__(self):
        self.history_log = []

    def add_history(self, op_str):
        self.history_log.append(op_str)
        if len(self.history_log) > 12:
            self.history_log.pop(0)

    def clear_history(self):
        self.history_log = []

    def draw_log(self, screen, font_small, font_mono):
        # Draw glass container
        w, h = LOG_RECT.width, LOG_RECT.height
        panel_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, COLOR_PANEL_FILL, (0, 0, w, h), border_radius=8)
        pygame.draw.rect(panel_surf, COLOR_PANEL_BORDER, (0, 0, w, h), 1, border_radius=8)
        screen.blit(panel_surf, LOG_RECT.topleft)
        
        title_text = font_small.render("RECENT OPERATIONS LOG", True, COLOR_TEXT)
        screen.blit(title_text, (LOG_RECT.x + 15, LOG_RECT.y + 12))
        
        start_y = LOG_RECT.y + 35
        for idx, entry in enumerate(self.history_log):
            item_y = start_y + idx * 13
            if item_y + 13 > LOG_RECT.y + LOG_RECT.height - 10:
                break
            
            if "Swap" in entry:
                col = COLOR_ACTION
            elif "Already" in entry or "complete" in entry or "Complete" in entry:
                col = COLOR_SUCCESS
            else:
                col = COLOR_TEXT_MUTED
                
            entry_surf = font_mono.render(entry, True, col)
            screen.blit(entry_surf, (LOG_RECT.x + 15, item_y))


# ==========================================
# CENTRAL COORDINATOR / GRAPHICS ENGINE
# ==========================================
class ArrayVisualizer:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=1)
        SoundEffects.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Odd-Even (Brick) Sort Space-Cyberpunk Visualizer")
        self.clock = pygame.time.Clock()
        
        self.stats_panel = StatisticsPanel()
        self.graph = ComplexityGraph()
        self.anim_manager = AnimationManager()
        
        self.array_size = 32
        self.original_array = []
        self.states = []
        self.current_state_idx = 0
        self.playing = False
        self.parallel_mode = False
        
        self.speed_levels = [1000, 600, 400, 250, 150, 80, 40, 20, 10, 2]
        self.speed_idx = 4
        self.step_timer = 0.0
        
        self.elements = []
        self.max_val = 100
        
        self.modal_active = False
        self.modal_input_text = ""
        self.modal_error = ""
        
        self.success_wave_timer = -1.0
        
        self.is_recording = False
        self.recorded_frames = []
        self.last_recorded_step = -1
        
        self.font_title = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.font_subtitle = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI", 14, bold=False)
        self.font_body_bold = pygame.font.SysFont("Segoe UI", 14, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI", 11, bold=False)
        self.font_mono = pygame.font.SysFont("Courier New", 11, bold=True)
        self.font_large_title = pygame.font.SysFont("Segoe UI", 48, bold=True)
        self.font_section_header = pygame.font.SysFont("Segoe UI", 20, bold=True)
        self.font_explanation = pygame.font.SysFont("Segoe UI", 18, bold=True)
        
        self.setup_buttons()
        self.randomize_array()

    def get_gradient_color(self, value):
        if self.max_val <= 0:
            return (100, 110, 140)
        ratio = max(0.0, min(1.0, value / self.max_val))
        hue = 230 + ratio * 120
        c = pygame.Color(0)
        c.hsla = (int(hue) % 360, 95, 55, 100)
        return (c.r, c.g, c.b)

    def setup_buttons(self):
        # Center buttons in BUTTONS_RECT
        y = BUTTONS_RECT.y + (BUTTONS_RECT.height - 40) // 2 # Centered vertically
        h = 40
        
        # Define the buttons and their widths in order
        button_specs = [
            ("play", "Play", self.toggle_play, 70),
            ("prev", "< Prev", self.step_backward, 70),
            ("next", "Next >", self.step_forward, 70),
            ("minus", "-", self.decrease_speed, 35),
            ("speed_space", "", None, 50), # Placeholder for speed text
            ("plus", "+", self.increase_speed, 35),
            ("size", f"Size: {self.array_size}", self.toggle_size, 90),
            ("mode", "Mode: Parallel" if self.parallel_mode else "Mode: Seq", self.toggle_mode, 110),
            ("gen", "Generate", self.randomize_array, 95),
            ("custom", "Custom Input", self.open_custom_modal, 110),
            ("export", "Export CSV", self.export_to_csv, 100)
        ]
        
        gap = 15
        total_width = sum(spec[3] for spec in button_specs) + gap * (len(button_specs) - 1)
        start_x = BUTTONS_RECT.x + (BUTTONS_RECT.width - total_width) // 2
        
        self.buttons = []
        current_x = start_x
        for name, text, callback, width in button_specs:
            if name == "speed_space":
                # Save the x-coordinate for speed text rendering
                self.speed_text_x = current_x + width // 2
                self.speed_text_y = y + h // 2
            else:
                btn = Button((current_x, y, width, h), text, callback)
                self.buttons.append(btn)
                if name == "play":
                    self.play_btn = btn
                elif name == "prev":
                    self.prev_btn = btn
                elif name == "next":
                    self.next_btn = btn
                elif name == "minus":
                    self.speed_down_btn = btn
                elif name == "plus":
                    self.speed_up_btn = btn
                elif name == "size":
                    self.size_btn = btn
                elif name == "mode":
                    self.mode_btn = btn
                elif name == "gen":
                    self.gen_btn = btn
                elif name == "custom":
                    self.custom_btn = btn
                elif name == "export":
                    self.export_btn = btn
            current_x += width + gap

    def randomize_array(self):
        self.playing = False
        self.play_btn.text = "Play"
        vals = [random.randint(10, 95) for _ in range(self.array_size)]
        self.original_array = [SortItem(idx, val) for idx, val in enumerate(vals)]
        self.compile_states()

    def toggle_size(self):
        sizes = [12, 16, 24, 32, 48, 64]
        curr_idx = sizes.index(self.array_size) if self.array_size in sizes else 3
        self.array_size = sizes[(curr_idx + 1) % len(sizes)]
        self.size_btn.text = f"Size: {self.array_size}"
        self.randomize_array()

    def toggle_mode(self):
        self.parallel_mode = not self.parallel_mode
        self.mode_btn.text = "Mode: Parallel" if self.parallel_mode else "Mode: Seq"
        self.compile_states()

    def compile_states(self):
        arr_copy = list(self.original_array)
        if self.parallel_mode:
            self.states = list(oddeven_parallel_generator(arr_copy))
        else:
            self.states = list(oddeven_seq_generator(arr_copy))
            
        self.current_state_idx = 0
        self.max_val = max(item.value for item in self.original_array) if self.original_array else 100
        
        self.success_wave_timer = -1.0
        self.anim_manager.clear()
        self.stats_panel.clear_history()
        
        self.elements = [
            Bar(val, i, self.max_val, len(self.original_array))
            for i, val in enumerate(self.original_array)
        ]
        self.update_elements_to_state()

    def update_elements_to_state(self):
        if not self.states:
            return
            
        state = self.states[self.current_state_idx]
        arr = state['arr']
        active = state['active']
        state_type = state['type']
        desc = state['desc']
        
        new_elements = []
        available = list(self.elements)
        
        for i, val in enumerate(arr):
            found_el = None
            for el in available:
                if el.id == val.id:
                    found_el = el
                    break
                    
            if found_el is not None:
                found_el.update_dimensions(i)
                new_elements.append(found_el)
                available.remove(found_el)
            else:
                el = Bar(val, i, self.max_val, len(arr))
                new_elements.append(el)
                
        self.elements = new_elements
        
        for i, el in enumerate(self.elements):
            if i % 2 == 0:
                el.target_color = COLOR_BAR_WHITE
            else:
                el.target_color = COLOR_BAR_BLACK
                
        if state_type == 'done':
            for el in self.elements:
                el.target_color = COLOR_SUCCESS
            
        spacing = 4 if len(arr) < 20 else (2 if len(arr) < 40 else 1)
        total_spacings = spacing * (len(arr) - 1)
        bar_w = (CANVAS_RECT.width - total_spacings) / len(arr)
        
        for idx in range(0, len(active) - 1, 2):
            i, j = active[idx], active[idx+1]
            if i < len(self.elements) and j < len(self.elements):
                el_i = self.elements[i]
                el_j = self.elements[j]
                if state_type in ['compare', 'compare_parallel', 'no_swap', 'no_swap_parallel']:
                    if el_i.value > el_j.value:
                        el_i.target_color = COLOR_ACTION
                        el_j.target_color = COLOR_ACTION
                    else:
                        el_i.target_color = COLOR_SUCCESS
                        el_j.target_color = COLOR_SUCCESS
                elif state_type in ['swap', 'swap_parallel']:
                    el_i.target_color = COLOR_ACTION
                    el_j.target_color = COLOR_ACTION
                    self.anim_manager.trigger_sparks(el_i.current_x + bar_w/2, el_i.current_y, COLOR_ACTION, count=6)
                    self.anim_manager.trigger_sparks(el_j.current_x + bar_w/2, el_j.current_y, COLOR_ACTION, count=6)
                    
        if state_type == 'no_swap' and len(active) >= 2:
            i, j = active[0], active[1]
            mx = (self.elements[i].current_x + self.elements[j].current_x + bar_w) / 2
            my = self.elements[i].current_y - 20
            self.anim_manager.trigger_checkmark(mx, my)
            SoundEffects.play_noswap()
            
        elif state_type == 'no_swap_parallel':
            for idx in range(0, len(active) - 1, 2):
                i, j = active[idx], active[idx+1]
                mx = (self.elements[i].current_x + self.elements[j].current_x + bar_w) / 2
                my = (self.elements[i].current_y + self.elements[j].current_y) / 2 - 20
                self.anim_manager.trigger_checkmark(mx, my)
            SoundEffects.play_noswap()
            
        if state_type in ['compare', 'compare_parallel']:
            SoundEffects.play_compare()
        elif state_type in ['swap', 'swap_parallel']:
            SoundEffects.play_compare()
            SoundEffects.play_swap()
        elif state_type == 'phase_start':
            SoundEffects.play_phase()
        elif state_type == 'done':
            SoundEffects.play_complete()
            self.success_wave_timer = 0.0
            
        self.stats_panel.add_history(desc)

    def toggle_play(self):
        self.playing = not self.playing
        self.play_btn.text = "Pause" if self.playing else "Play"

    def step_forward(self):
        self.playing = False
        self.play_btn.text = "Play"
        if self.current_state_idx < len(self.states) - 1:
            self.current_state_idx += 1
            self.update_elements_to_state()

    def step_backward(self):
        self.playing = False
        self.play_btn.text = "Play"
        if self.current_state_idx > 0:
            self.current_state_idx -= 1
            self.update_elements_to_state()

    def increase_speed(self):
        if self.speed_idx < len(self.speed_levels) - 1:
            self.speed_idx += 1

    def decrease_speed(self):
        if self.speed_idx > 0:
            self.speed_idx -= 1

    def open_custom_modal(self):
        self.playing = False
        self.play_btn.text = "Play"
        self.modal_active = True
        self.modal_input_text = ""
        self.modal_error = ""

    def close_custom_modal(self, submit=False):
        if submit:
            try:
                tokens = self.modal_input_text.split(',')
                parsed = []
                for tok in tokens:
                    tok = tok.strip()
                    if not tok:
                        continue
                    val = int(tok)
                    if val <= 0:
                        raise ValueError("Numbers must be positive.")
                    if val > 500:
                        raise ValueError("Values must be <= 500.")
                    parsed.append(val)
                    
                if len(parsed) < 4:
                    raise ValueError("Enter at least 4 numbers.")
                if len(parsed) > 100:
                    raise ValueError("Maximum 100 numbers allowed.")
                    
                self.original_array = [SortItem(idx, val) for idx, val in enumerate(parsed)]
                self.array_size = len(parsed)
                self.size_btn.text = f"Size: {self.array_size}"
                self.compile_states()
                self.modal_active = False
            except ValueError as e:
                self.modal_error = str(e)
            except Exception:
                self.modal_error = "Use comma-separated integers."
        else:
            self.modal_active = False

    def export_to_csv(self):
        filename = "odd_even_sort_metrics.csv"
        try:
            file_exists = os.path.exists(filename)
            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Array Size", "Mode", "Comparisons", "Swaps", "Cycles"])
                
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                mode = "Parallel" if self.parallel_mode else "Sequential"
                curr_state = self.states[self.current_state_idx] if self.states else {}
                writer.writerow([
                    timestamp,
                    self.array_size,
                    mode,
                    curr_state.get('comps', 0),
                    curr_state.get('swaps', 0),
                    curr_state.get('cycle', 0)
                ])
            self.stats_panel.add_history("CSV Metrics Exported successfully.")
        except Exception as e:
            print("CSV Export failed:", e)
            self.stats_panel.add_history("CSV Export failed.")

    def handle_recording(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.recorded_frames = []
            self.last_recorded_step = -1
            self.stats_panel.add_history("Recording started...")
        else:
            self.stats_panel.add_history("Compiling GIF animation...")
            self.save_recorded_gif()

    def save_recorded_gif(self):
        if not self.recorded_frames:
            self.stats_panel.add_history("No frames captured.")
            return
            
        self.screen.fill(COLOR_BG)
        txt = self.font_subtitle.render("SAVING ANIMATION TO GIF... PLEASE WAIT", True, COLOR_HIGHLIGHT)
        rect = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(txt, rect)
        pygame.display.flip()
        
        try:
            import PIL.Image
            pil_frames = []
            for frame in self.recorded_frames:
                scaled = pygame.transform.smoothscale(frame, (640, 360))
                if hasattr(pygame.image, 'tobytes'):
                    raw = pygame.image.tobytes(scaled, 'RGB')
                else:
                    raw = pygame.image.tostring(scaled, 'RGB')
                img = PIL.Image.frombytes('RGB', (640, 360), raw)
                pil_frames.append(img)
                
            out_path = "odd_even_sort.gif"
            delay_ms = max(100, self.speed_levels[self.speed_idx])
            
            pil_frames[0].save(
                out_path,
                save_all=True,
                append_images=pil_frames[1:],
                optimize=True,
                duration=delay_ms,
                loop=0
            )
            self.stats_panel.add_history(f"Animation saved to {out_path}")
        except Exception as e:
            print("GIF Export failed:", e)
            self.stats_panel.add_history("Failed to save GIF.")
            
        self.recorded_frames = []

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.update(mouse_pos)
            
        self.anim_manager.update(dt)
        
        for el in self.elements:
            el.update(dt)
            
        if pygame.mouse.get_pressed()[0] and not self.modal_active:
            slider_x = 40
            slider_y = 665
            slider_w = 1200
            if slider_x <= mouse_pos[0] <= slider_x + slider_w and slider_y - 12 <= mouse_pos[1] <= slider_y + 12:
                ratio = (mouse_pos[0] - slider_x) / slider_w
                self.current_state_idx = int(ratio * (len(self.states) - 1))
                self.current_state_idx = max(0, min(len(self.states) - 1, self.current_state_idx))
                self.update_elements_to_state()
                
        if self.playing and not self.modal_active:
            self.step_timer += dt * 1000.0
            delay = self.speed_levels[self.speed_idx]
            if self.step_timer >= delay:
                self.step_timer = 0.0
                if self.current_state_idx < len(self.states) - 1:
                    self.current_state_idx += 1
                    self.update_elements_to_state()
                else:
                    self.playing = False
                    self.play_btn.text = "Play"
                    
        if self.success_wave_timer >= 0.0:
            self.success_wave_timer += dt * 30.0
            for i, el in enumerate(self.elements):
                if i < self.success_wave_timer:
                    el.target_color = COLOR_SUCCESS
                    
        if self.is_recording and self.state_changed():
            self.recorded_frames.append(self.screen.copy())
            self.last_recorded_step = self.current_state_idx

    def state_changed(self):
        return self.current_state_idx != self.last_recorded_step

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                pygame.quit()
                sys.exit(0)
                
            if event.type == pygame.KEYDOWN:
                if self.modal_active:
                    if event.key == pygame.K_RETURN:
                        self.close_custom_modal(submit=True)
                    elif event.key == pygame.K_BACKSPACE:
                        self.modal_input_text = self.modal_input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.close_custom_modal(submit=False)
                    else:
                        if event.unicode in "0123456789,":
                            self.modal_input_text += event.unicode
                    continue
                    
                if event.key == pygame.K_SPACE:
                    self.toggle_play()
                elif event.key == pygame.K_RIGHT:
                    self.step_forward()
                elif event.key == pygame.K_LEFT:
                    self.step_backward()
                elif event.key == pygame.K_r:
                    self.compile_states()
                elif event.key == pygame.K_n:
                    self.randomize_array()
                elif event.key == pygame.K_p:
                    self.toggle_mode()
                elif event.key == pygame.K_e:
                    self.export_to_csv()
                elif event.key == pygame.K_f:
                    self.handle_recording()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                    
            if not self.modal_active:
                for btn in self.buttons:
                    btn.handle_event(event)

    def draw_glass_panel(self, rect, fill_color=COLOR_PANEL_FILL, border_color=COLOR_PANEL_BORDER, radius=8):
        x, y, w, h = rect
        temp_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(temp_surf, fill_color, (0, 0, w, h), border_radius=radius)
        pygame.draw.rect(temp_surf, border_color, (0, 0, w, h), 1, border_radius=radius)
        self.screen.blit(temp_surf, (x, y))

    def draw_custom_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        
        mw, mh = 620, 240
        mx = (SCREEN_WIDTH - mw) // 2
        my = (SCREEN_HEIGHT - mh) // 2
        self.draw_glass_panel((mx, my, mw, mh), fill_color=(22, 27, 34, 245), border_color=COLOR_PANEL_BORDER, radius=10)
        
        hdr = self.font_subtitle.render("ENTER CUSTOM DATA ARRAY (COMMA-SEPARATED):", True, COLOR_HIGHLIGHT)
        self.screen.blit(hdr, (mx + 30, my + 30))
        
        tb_rect = pygame.Rect(mx + 30, my + 70, mw - 60, 45)
        pygame.draw.rect(self.screen, (13, 17, 23), tb_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_SELECT, tb_rect, 1, border_radius=6)
        
        content_surf = self.font_mono.render(self.modal_input_text + "|", True, COLOR_TEXT)
        self.screen.blit(content_surf, (tb_rect.x + 15, tb_rect.y + 14))
        
        if self.modal_error:
            err_surf = self.font_small.render(self.modal_error, True, COLOR_ACTION)
            self.screen.blit(err_surf, (mx + 30, my + 125))
        else:
            hint_surf = self.font_small.render("Example: 22, 10, 16, 28, 46, 34. Values must be <= 500.", True, COLOR_TEXT_MUTED)
            self.screen.blit(hint_surf, (mx + 30, my + 125))
            
        btn_y = my + mh - 70
        ok_rect = pygame.Rect(mx + mw - 250, btn_y, 100, 36)
        cancel_rect = pygame.Rect(mx + mw - 130, btn_y, 100, 36)
        
        pygame.draw.rect(self.screen, (33, 38, 45), ok_rect, border_radius=6)
        pygame.draw.rect(self.screen, (33, 38, 45), cancel_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, ok_rect, 1, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, cancel_rect, 1, border_radius=6)
        
        ok_text = self.font_body_bold.render("OK", True, COLOR_TEXT)
        cancel_text = self.font_body_bold.render("Cancel", True, COLOR_TEXT)
        self.screen.blit(ok_text, ok_text.get_rect(center=ok_rect.center))
        self.screen.blit(cancel_text, cancel_text.get_rect(center=cancel_rect.center))
        
        m_pressed = pygame.mouse.get_pressed()
        m_pos = pygame.mouse.get_pos()
        if m_pressed[0]:
            if ok_rect.collidepoint(m_pos):
                self.close_custom_modal(submit=True)
                pygame.time.delay(100)
            elif cancel_rect.collidepoint(m_pos):
                self.close_custom_modal(submit=False)
                pygame.time.delay(100)

    def draw(self):
        self.screen.fill(COLOR_BG)
        self.anim_manager.draw_bg_stars(self.screen)
        
        # Parse current state for header display
        curr_state = self.states[self.current_state_idx] if self.states else {}
        comps = curr_state.get('comps', 0)
        swaps = curr_state.get('swaps', 0)
        cycle = curr_state.get('cycle', 0)
        phase = curr_state.get('phase', 'IDLE')
        state_type = curr_state.get('type', '')
        active = curr_state.get('active', [])
        n = self.array_size
        
        phase_text = ""
        large_text = ""
        explain_text = ""
        text_color = COLOR_TEXT_MUTED
        
        if phase != 'IDLE':
            phase_text = f"{phase} PHASE"
            
        if state_type in ['compare', 'no_swap', 'swap'] and len(active) >= 2:
            i, j = active[0], active[1]
            if i < len(self.elements) and j < len(self.elements):
                val_i = self.elements[i].value
                val_j = self.elements[j].value
                
                if state_type == 'swap':
                    large_text = f"{val_j} > {val_i}"
                    explain_text = f"Swap pair {i}-{j}"
                    text_color = COLOR_ACTION
                elif val_i > val_j:
                    large_text = f"{val_i} > {val_j}"
                    explain_text = "Wrong order, swap next"
                    text_color = COLOR_ACTION
                else:
                    large_text = f"{val_i} <= {val_j}"
                    explain_text = "Correct order, skip"
                    text_color = COLOR_SUCCESS
        elif state_type in ['compare_parallel', 'swap_parallel', 'no_swap_parallel'] and len(active) >= 2:
            num_pairs = len(active) // 2
            large_text = f"Comparing {num_pairs} Pairs"
            if state_type == 'swap_parallel':
                explain_text = "Performing parallel swaps"
                text_color = COLOR_ACTION
            elif state_type == 'compare_parallel':
                explain_text = "Parallel comparison of all pairs"
                text_color = COLOR_SELECT
            else:
                explain_text = "All pairs in order, skipping"
                text_color = COLOR_SUCCESS
        elif state_type == 'done':
            phase_text = "SORTING COMPLETE"
            large_text = "Array Sorted"
            explain_text = f"Total Compares: {comps}  |  Total Swaps: {swaps}"
            text_color = COLOR_SUCCESS
        elif state_type == 'phase_start':
            phase_text = f"STARTING {phase} PHASE"
            large_text = f"Cycle {cycle}"
            explain_text = "Preparing to compare elements"
            text_color = COLOR_SELECT
        else:
            phase_text = "ODD-EVEN SORT"
            large_text = f"Size: {self.array_size}"
            explain_text = "Press Play or Step to visualize"
            text_color = COLOR_TEXT_MUTED

        # Render Title & Subtitle at the top (centered)
        title_surf = self.font_subtitle.render("Odd-Even Sort", True, COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 35))
        self.screen.blit(title_surf, title_rect)
        
        sub_surf = self.font_small.render("Kinetic short explanation", True, COLOR_TEXT_MUTED)
        sub_rect = sub_surf.get_rect(center=(SCREEN_WIDTH // 2, 58))
        self.screen.blit(sub_surf, sub_rect)
        
        # Render centered state explanation texts
        if phase_text:
            phase_surf = self.font_section_header.render(phase_text, True, text_color)
            phase_rect = phase_surf.get_rect(center=(SCREEN_WIDTH // 2, 105))
            self.screen.blit(phase_surf, phase_rect)
            
        if large_text:
            large_surf = self.font_large_title.render(large_text, True, COLOR_TEXT)
            large_rect = large_surf.get_rect(center=(SCREEN_WIDTH // 2, 150))
            self.screen.blit(large_surf, large_rect)
            
        if explain_text:
            explain_surf = self.font_explanation.render(explain_text, True, text_color)
            explain_rect = explain_surf.get_rect(center=(SCREEN_WIDTH // 2, 200))
            self.screen.blit(explain_surf, explain_rect)
        
        # Buttons Panel
        self.draw_glass_panel(BUTTONS_RECT)
        for btn in self.buttons:
            btn.draw(self.screen, self.font_body_bold)
            
        # Speed Level inside the buttons panel
        speed_str = f"{len(self.speed_levels) - self.speed_idx}x"
        speed_surf = self.font_body_bold.render(speed_str, True, COLOR_TEXT)
        speed_rect = speed_surf.get_rect(center=(self.speed_text_x, self.speed_text_y))
        self.screen.blit(speed_surf, speed_rect)
        
        if self.is_recording:
            pygame.draw.circle(self.screen, COLOR_ACTION, (HEADER_RECT.x + HEADER_RECT.width - 20, HEADER_RECT.y + 18), 5)
            
        # Canvas Panel
        self.draw_glass_panel(CANVAS_RECT)
        
        # Draw bars
        spacing = 4 if n < 20 else (2 if n < 40 else 1)
        total_spacings = spacing * (n - 1)
        bar_w = (CANVAS_RECT.width - total_spacings) / n
        active = curr_state.get('active', [])
        
        for i, el in enumerate(self.elements):
            is_active = (i in active)
            el.draw(self.screen, bar_w, self.font_body_bold, self.font_small, is_active=is_active)
            
        # Glowing operations and labels on active bars
        if state_type := curr_state.get('type', ''):
            if state_type in ['compare', 'no_swap'] and len(active) >= 2:
                i, j = active[0], active[1]
                if i < len(self.elements) and j < len(self.elements):
                    bx1 = self.elements[i].current_x + bar_w/2
                    bx2 = self.elements[j].current_x + bar_w/2
                    by = (self.elements[i].current_y + self.elements[i].height/2 + self.elements[j].current_y + self.elements[j].height/2) / 2
                    conn_color = COLOR_ACTION if self.elements[i].value > self.elements[j].value else COLOR_SUCCESS
                    self.anim_manager.draw_glowing_connection(self.screen, bx1, by, bx2, by, conn_color)
                    
                    comp_lbl = self.font_body_bold.render("COMPARE", True, (255, 255, 255))
                    lbl_rect = comp_lbl.get_rect(center=((bx1 + bx2) / 2, by))
                    self.screen.blit(comp_lbl, lbl_rect)
                
            elif state_type == 'swap' and len(active) >= 2:
                i, j = active[0], active[1]
                if i < len(self.elements) and j < len(self.elements):
                    bx1 = self.elements[i].current_x + bar_w/2
                    bx2 = self.elements[j].current_x + bar_w/2
                    y_base = CANVAS_RECT.y + CANVAS_RECT.height - 35
                    self.anim_manager.draw_swap_arrow(self.screen, bx1, y_base, bx2, COLOR_ACTION)
                    
                    by = (self.elements[i].current_y + self.elements[i].height/2 + self.elements[j].current_y + self.elements[j].height/2) / 2
                    swap_lbl = self.font_body_bold.render("SWAP", True, (255, 255, 255))
                    lbl_rect = swap_lbl.get_rect(center=((bx1 + bx2) / 2, by))
                    self.screen.blit(swap_lbl, lbl_rect)
                
            elif state_type == 'compare_parallel':
                for idx in range(0, len(active) - 1, 2):
                    i, j = active[idx], active[idx+1]
                    if i < len(self.elements) and j < len(self.elements):
                        bx1 = self.elements[i].current_x + bar_w/2
                        bx2 = self.elements[j].current_x + bar_w/2
                        by = (self.elements[i].current_y + self.elements[i].height/2 + self.elements[j].current_y + self.elements[j].height/2) / 2
                        pair_color = COLOR_ACTION if self.elements[i].value > self.elements[j].value else COLOR_SUCCESS
                        self.anim_manager.draw_glowing_connection(self.screen, bx1, by, bx2, by, pair_color)
                        
                        comp_lbl = self.font_body_bold.render("COMPARE", True, (255, 255, 255))
                        lbl_rect = comp_lbl.get_rect(center=((bx1 + bx2) / 2, by))
                        self.screen.blit(comp_lbl, lbl_rect)
                    
            elif state_type == 'swap_parallel':
                for idx in range(0, len(active) - 1, 2):
                    i, j = active[idx], active[idx+1]
                    if i < len(self.elements) and j < len(self.elements):
                        bx1 = self.elements[i].current_x + bar_w/2
                        bx2 = self.elements[j].current_x + bar_w/2
                        y_base = CANVAS_RECT.y + CANVAS_RECT.height - 35
                        self.anim_manager.draw_swap_arrow(self.screen, bx1, y_base, bx2, COLOR_ACTION)
                        
                        by = (self.elements[i].current_y + self.elements[i].height/2 + self.elements[j].current_y + self.elements[j].height/2) / 2
                        swap_lbl = self.font_body_bold.render("SWAP", True, (255, 255, 255))
                        lbl_rect = swap_lbl.get_rect(center=((bx1 + bx2) / 2, by))
                        self.screen.blit(swap_lbl, lbl_rect)

        self.anim_manager.draw_effects(self.screen)
        
        if self.parallel_mode:
            p_note = self.font_body_bold.render("Concurrent Mode: Multi-node sorting in parallel", True, COLOR_SELECT)
            self.screen.blit(p_note, (CANVAS_RECT.x + 15, CANVAS_RECT.y + 15))
            
        # Bottom details panel
        self.draw_glass_panel(DETAILS_RECT)
        
        total_steps = len(self.states)
        curr_step = self.current_state_idx + 1 if total_steps > 0 else 0
        step_surf = self.font_body_bold.render(f"Step {curr_step} / {total_steps}", True, COLOR_TEXT)
        self.screen.blit(step_surf, (DETAILS_RECT.x + 20, DETAILS_RECT.y + 15))
        
        # Slider (repositioned inside details panel)
        slider_x = DETAILS_RECT.x + 20
        slider_y = DETAILS_RECT.y + 60
        slider_w = DETAILS_RECT.width - 40
        slider_h = 6
        pygame.draw.rect(self.screen, (33, 38, 45), (slider_x, slider_y, slider_w, slider_h), border_radius=3)
        
        ratio = (self.current_state_idx / (total_steps - 1)) if total_steps > 1 else 0.0
        knob_x = slider_x + int(ratio * slider_w)
        pygame.draw.circle(self.screen, COLOR_SELECT, (knob_x, slider_y + slider_h//2), 8)
        
        if self.modal_active:
            self.draw_custom_modal()
            
        pygame.display.flip()

    def run(self):
        last_time = time.time()
        while True:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            dt = min(0.05, dt)
            
            self.handle_events()
            self.update(dt)
            self.draw()
            self.clock.tick(FPS)


# ==========================================
# BOOTSTRAPPING ENTRY POINT
# ==========================================
def main():
    try:
        visualizer = ArrayVisualizer()
        visualizer.run()
    except Exception as e:
        print(f"An unexpected error occurred during execution: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
