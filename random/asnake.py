import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
import json
import os
import time
import platform

# Detect platform
PLATFORM = platform.system().lower()
print(f"Snake AI running on: {PLATFORM}")

# Try to import pygame, but make it optional and verify font availability
PYGAME_AVAILABLE = False
try:
    import pygame
    # Try to initialize pygame and the font subsystem; if font isn't available
    # disable visualization gracefully.
    try:
        pygame.init()
        try:
            pygame.font.init()
        except Exception:
            # Some pygame builds may not have font support (or SDL_ttf missing)
            raise
        if not getattr(pygame, 'font', None) or not pygame.font.get_init():
            raise ImportError('pygame.font not available')
    except Exception as e:
        print(f"pygame imported but font subsystem unavailable: {e}")
        PYGAME_AVAILABLE = False
    else:
        PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame not installed. Running in headless mode (no visualization).")
    print("To enable visualization: pip install pygame")

# Load configuration
def load_config(config_path="random/snake_config.json"):
    with open(config_path, 'r') as f:
        return json.load(f)

CONFIG = load_config()

# Extract config values
GRID_SIZE = CONFIG['game']['grid_size']
CELL_SIZE = CONFIG['game']['cell_size']
GAME_SPEED = CONFIG['game']['game_speed']
STARTING_LENGTH = CONFIG['game']['starting_length']

EPISODES = CONFIG['training']['episodes']
MAX_STEPS = CONFIG['training']['max_steps_per_episode']
SAVE_INTERVAL = CONFIG['training']['save_interval']
MODEL_DIR = CONFIG['training']['model_dir']
MODEL_NAME = CONFIG['training']['model_name']

LEARNING_RATE = CONFIG['agent']['learning_rate']
GAMMA = CONFIG['agent']['gamma']
EPSILON_START = CONFIG['agent']['epsilon_start']
EPSILON_END = CONFIG['agent']['epsilon_end']
EPSILON_DECAY = CONFIG['agent']['epsilon_decay']
MEMORY_SIZE = CONFIG['agent']['memory_size']
BATCH_SIZE = CONFIG['agent']['batch_size']
TARGET_UPDATE = CONFIG['agent']['target_update_frequency']

REWARD_APPLE = CONFIG['rewards']['apple']
REWARD_DEATH = CONFIG['rewards']['death']
REWARD_CLOSER = CONFIG['rewards']['closer_to_apple']
REWARD_FARTHER = CONFIG['rewards']['farther_from_apple']
REWARD_STEP = CONFIG['rewards']['step']

SHOW_GAME = CONFIG['display']['show_game'] and PYGAME_AVAILABLE
DISPLAY_INTERVAL = CONFIG['display'].get('display_interval', 1)
TIME_UPDATE_INTERVAL = CONFIG['display'].get('time_update_interval', 1)
WINDOW_WIDTH = CONFIG['display'].get('window_width', GRID_SIZE * CELL_SIZE)
WINDOW_HEIGHT = CONFIG['display'].get('window_height', GRID_SIZE * CELL_SIZE)
# Support both old single value and new horizontal/vertical values
PARALLEL_GAMES_H = CONFIG['display'].get('parallel_games_horizontal', CONFIG['display'].get('parallel_games', 1))
PARALLEL_GAMES_V = CONFIG['display'].get('parallel_games_vertical', CONFIG['display'].get('parallel_games', 1))
BG_COLOR = tuple(CONFIG['display']['background_color'])
SNAKE_COLOR = tuple(CONFIG['display']['snake_color'])
APPLE_COLOR = tuple(CONFIG['display']['apple_color'])
GRID_COLOR = tuple(CONFIG['display']['grid_color'])

# Directions: UP, RIGHT, DOWN, LEFT
DIRECTIONS = [
    np.array([0, -1]),   # UP
    np.array([1, 0]),    # RIGHT
    np.array([0, 1]),    # DOWN
    np.array([-1, 0])    # LEFT
]

class SnakeGame:
    def __init__(self, grid_size=GRID_SIZE, starting_length=STARTING_LENGTH):
        self.grid_size = grid_size
        self.starting_length = starting_length
        self.reset()
        
    def reset(self):
        """Reset the game to initial state."""
        # Start snake in the middle, heading right
        start_x = self.grid_size // 2
        start_y = self.grid_size // 2
        
        self.snake = deque()
        for i in range(self.starting_length):
            self.snake.append(np.array([start_x - i, start_y]))
        
        self.direction = 1  # RIGHT
        self.score = 0
        self.steps = 0
        self.steps_since_apple = 0  # Track steps without eating apple
        self.place_apple()
        self.prev_distance = self._distance_to_apple()
        
        return self.get_state()
    
    def place_apple(self):
        """Place apple at random empty position."""
        while True:
            self.apple = np.array([
                random.randint(0, self.grid_size - 1),
                random.randint(0, self.grid_size - 1)
            ])
            # Check if apple is not on snake
            if not any(np.array_equal(self.apple, segment) for segment in self.snake):
                break
    
    def _distance_to_apple(self):
        """Manhattan distance from head to apple."""
        head = self.snake[0]
        return abs(head[0] - self.apple[0]) + abs(head[1] - self.apple[1])
    
    def step(self, action):
        """
        Take action: 0=straight, 1=turn right, 2=turn left
        Returns: (state, reward, done)
        """
        self.steps += 1
        self.steps_since_apple += 1
        
        # Update direction based on action
        if action == 1:  # Turn right
            self.direction = (self.direction + 1) % 4
        elif action == 2:  # Turn left
            self.direction = (self.direction - 1) % 4
        # action == 0: go straight (no change)
        
        # Move snake
        head = self.snake[0]
        new_head = head + DIRECTIONS[self.direction]
        
        # Check wall collision
        if (new_head[0] < 0 or new_head[0] >= self.grid_size or
            new_head[1] < 0 or new_head[1] >= self.grid_size):
            return self.get_state(), REWARD_DEATH, True
        
        # Check self collision
        if any(np.array_equal(new_head, segment) for segment in self.snake):
            return self.get_state(), REWARD_DEATH, True
        
        # Move snake
        self.snake.appendleft(new_head)
        
        # Check if apple eaten
        ate_apple = np.array_equal(new_head, self.apple)
        
        if ate_apple:
            self.score += 1
            self.steps_since_apple = 0  # Reset counter
            self.place_apple()
            reward = REWARD_APPLE
        else:
            self.snake.pop()  # Remove tail if no apple eaten
            
            # Reward for getting closer to apple
            current_distance = self._distance_to_apple()
            if current_distance < self.prev_distance:
                reward = REWARD_CLOSER
            else:
                reward = REWARD_FARTHER
            self.prev_distance = current_distance
        
        # Small penalty for each step to encourage efficiency
        reward += REWARD_STEP
        
        # IMPORTANT: Penalize the snake for not making progress toward apple
        # If snake hasn't eaten in too long relative to distance, it's probably stuck in a loop
        max_reasonable_steps = self._distance_to_apple() * 4 + 100
        if self.steps_since_apple > max_reasonable_steps:
            reward -= 5  # Penalty for wasting time
        
        # Check if game should end (too many steps without progress)
        done = self.steps >= MAX_STEPS or self.steps_since_apple > max_reasonable_steps * 2
        
        return self.get_state(), reward, done
    
    def get_state(self):
        """
        Get state representation (11 values):
        - Danger straight, right, left (3)
        - Direction: up, right, down, left (4)
        - Apple direction: left, right, up, down (4)
        """
        head = self.snake[0]
        
        # Check danger in each direction relative to current direction
        point_straight = head + DIRECTIONS[self.direction]
        point_right = head + DIRECTIONS[(self.direction + 1) % 4]
        point_left = head + DIRECTIONS[(self.direction - 1) % 4]
        
        danger_straight = self._is_collision(point_straight)
        danger_right = self._is_collision(point_right)
        danger_left = self._is_collision(point_left)
        
        # Current direction (one-hot encoded)
        dir_up = self.direction == 0
        dir_right = self.direction == 1
        dir_down = self.direction == 2
        dir_left = self.direction == 3
        
        # Apple location relative to head
        apple_left = self.apple[0] < head[0]
        apple_right = self.apple[0] > head[0]
        apple_up = self.apple[1] < head[1]
        apple_down = self.apple[1] > head[1]
        
        state = np.array([
            danger_straight, danger_right, danger_left,
            dir_up, dir_right, dir_down, dir_left,
            apple_left, apple_right, apple_up, apple_down
        ], dtype=np.float32)
        
        return state
    
    def _is_collision(self, point):
        """Check if point is a collision (wall or self)."""
        # Wall collision
        if (point[0] < 0 or point[0] >= self.grid_size or
            point[1] < 0 or point[1] >= self.grid_size):
            return True
        
        # Self collision
        if any(np.array_equal(point, segment) for segment in self.snake):
            return True
        
        return False


class DQN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


class ReplayMemory:
    def __init__(self, capacity):
        self.memory = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)
    
    def __len__(self):
        return len(self.memory)


class SnakeAgent:
    def __init__(self, state_size=11, action_size=3, hidden_size=256):
        self.state_size = state_size
        self.action_size = action_size
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Q-Networks
        self.policy_net = DQN(state_size, hidden_size, action_size).to(self.device)
        self.target_net = DQN(state_size, hidden_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=LEARNING_RATE)
        self.memory = ReplayMemory(MEMORY_SIZE)
        
        self.epsilon = EPSILON_START
        self.steps_done = 0
        
    def select_action(self, state, training=True):
        """Select action using epsilon-greedy policy."""
        if training and random.random() < self.epsilon:
            return random.randrange(self.action_size)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()
    
    def train_step(self):
        """Perform one training step."""
        if len(self.memory) < BATCH_SIZE:
            return 0
        
        # Sample batch
        batch = self.memory.sample(BATCH_SIZE)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).unsqueeze(1).to(self.device)
        
        # Current Q values
        current_q = self.policy_net(states).gather(1, actions)
        
        # Target Q values
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1, keepdim=True)[0]
            target_q = rewards + (1 - dones) * GAMMA * next_q
        
        # Compute loss
        loss = nn.MSELoss()(current_q, target_q)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        return loss.item()
    
    def update_target_network(self):
        """Copy weights from policy network to target network."""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def decay_epsilon(self):
        """Decay exploration rate."""
        self.epsilon = max(EPSILON_END, self.epsilon * EPSILON_DECAY)
    
    def save(self, path):
        """Save model."""
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps_done': self.steps_done
        }, path)
        
    def load(self, path):
        """Load model."""
        checkpoint = torch.load(path)
        self.policy_net.load_state_dict(checkpoint['policy_net'])
        self.target_net.load_state_dict(checkpoint['target_net'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.epsilon = checkpoint['epsilon']
        self.steps_done = checkpoint['steps_done']


class SnakeVisualizer:
    def __init__(self, window_width=WINDOW_WIDTH, window_height=WINDOW_HEIGHT, 
                 grid_size=GRID_SIZE, parallel_games_h=PARALLEL_GAMES_H, parallel_games_v=PARALLEL_GAMES_V):
        if not PYGAME_AVAILABLE:
            return
        
        pygame.init()
        self.grid_size = grid_size
        self.parallel_games_h = parallel_games_h  # Horizontal count
        self.parallel_games_v = parallel_games_v  # Vertical count
        
        # Reserve space for info bar at bottom
        self.info_bar_height = 60
        self.games_height = window_height - self.info_bar_height
        self.window_width = window_width
        self.window_height = window_height
        
        # Calculate cell size based on window dimensions and parallel games
        if parallel_games_h > 1 or parallel_games_v > 1:
            # Split window into parallel_games_h x parallel_games_v grid
            available_width = window_width // parallel_games_h
            available_height = self.games_height // parallel_games_v
            self.cell_size = min(available_width, available_height) // grid_size
        else:
            # Single game uses full window
            self.cell_size = min(window_width, self.games_height) // grid_size
        
        self.screen = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption('Snake AI Training')
        self.clock = pygame.time.Clock()
        
        # Store multiple games for parallel display
        self.games = []
        
    def draw(self, game, episode, score, epsilon):
        """Draw a single game state."""
        if not PYGAME_AVAILABLE:
            return True
        
        self.screen.fill(BG_COLOR)
        
        # Calculate offset for this game (if displaying multiple)
        game_index = 0  # For single game display
        row = game_index // self.parallel_games_h
        col = game_index % self.parallel_games_h
        offset_x = col * (self.window_width // self.parallel_games_h)
        offset_y = row * (self.window_height // self.parallel_games_v)
        
        # Draw grid
        for x in range(0, self.grid_size * self.cell_size, self.cell_size):
            pygame.draw.line(self.screen, GRID_COLOR, 
                           (offset_x + x, offset_y), 
                           (offset_x + x, offset_y + self.grid_size * self.cell_size))
        for y in range(0, self.grid_size * self.cell_size, self.cell_size):
            pygame.draw.line(self.screen, GRID_COLOR, 
                           (offset_x, offset_y + y), 
                           (offset_x + self.grid_size * self.cell_size, offset_y + y))
        
        # Draw snake
        for i, segment in enumerate(game.snake):
            x = offset_x + segment[0] * self.cell_size
            y = offset_y + segment[1] * self.cell_size
            # Head is brighter
            if i == 0:
                color = tuple(min(255, c + 50) for c in SNAKE_COLOR)
            else:
                color = SNAKE_COLOR
            pygame.draw.rect(self.screen, color, (x, y, self.cell_size-1, self.cell_size-1))
        
        # Draw apple
        x = offset_x + game.apple[0] * self.cell_size
        y = offset_y + game.apple[1] * self.cell_size
        pygame.draw.rect(self.screen, APPLE_COLOR, (x, y, self.cell_size-1, self.cell_size-1))
        
        # Draw info text (if font subsystem available)
        try:
            if getattr(pygame, 'font', None) and pygame.font.get_init():
                font = pygame.font.Font(None, 36)
                text = font.render(f'Episode: {episode} | Score: {score} | ε: {epsilon:.3f}', True, (255, 255, 255))
                self.screen.blit(text, (10, 10))
        except Exception:
            # If rendering fails for any reason, skip text rendering silently
            pass
        
        pygame.display.flip()
        self.clock.tick(GAME_SPEED)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True
    
    def draw_parallel(self, games_data, total_episodes=0, total_target=0, 
                      elapsed_time=0, remaining_time=0, best_score=0):
        """Draw multiple games in parallel with info bar.
        
        Args:
            games_data: list of (game, episode, score, epsilon) tuples
            total_episodes: total episodes completed across all games
            total_target: total target episodes (num_games * episodes_per_game)
            elapsed_time: time elapsed in seconds
            remaining_time: estimated remaining time in seconds
            best_score: best score achieved so far
        """
        if not PYGAME_AVAILABLE:
            return True
        
        self.screen.fill(BG_COLOR)
        
        # Debug: print once
        if not hasattr(self, '_debug_printed'):
            self._debug_printed = True
            print(f"DEBUG draw_parallel: H={self.parallel_games_h} x V={self.parallel_games_v}, games to draw={len(games_data)}")
            print(f"DEBUG draw_parallel: sub_width={self.window_width // self.parallel_games_h}, "
                  f"sub_height={self.games_height // self.parallel_games_v}")
        
        # Calculate dimensions for each sub-game
        sub_width = self.window_width // self.parallel_games_h
        sub_height = self.games_height // self.parallel_games_v
        # Calculate cell size to maximize use of space
        cell_size_w = sub_width // self.grid_size
        cell_size_h = sub_height // self.grid_size
        cell_size = min(cell_size_w, cell_size_h)
        
        # Calculate actual grid dimensions (centered in sub-region)
        grid_pixel_width = self.grid_size * cell_size
        grid_pixel_height = self.grid_size * cell_size
        
        max_games = self.parallel_games_h * self.parallel_games_v
        for idx, (game, episode, score, epsilon) in enumerate(games_data[:max_games]):
            row = idx // self.parallel_games_h
            col = idx % self.parallel_games_h
            offset_x = col * sub_width
            offset_y = row * sub_height
            
            # Draw clear border around this game (thick white lines)
            border_color = (255, 255, 255)
            border_thickness = 3
            # Top border
            pygame.draw.line(self.screen, border_color, 
                           (offset_x, offset_y), 
                           (offset_x + sub_width, offset_y), border_thickness)
            # Left border
            pygame.draw.line(self.screen, border_color, 
                           (offset_x, offset_y), 
                           (offset_x, offset_y + sub_height), border_thickness)
            # Right border (only if not last column)
            if col < self.parallel_games_h - 1:
                pygame.draw.line(self.screen, border_color, 
                               (offset_x + sub_width - 1, offset_y), 
                               (offset_x + sub_width - 1, offset_y + sub_height), border_thickness)
            # Bottom border (only if not last row)
            if row < self.parallel_games_v - 1:
                pygame.draw.line(self.screen, border_color, 
                               (offset_x, offset_y + sub_height - 1), 
                               (offset_x + sub_width, offset_y + sub_height - 1), border_thickness)
            
            # Draw grid for this game
            for x in range(0, grid_pixel_width + 1, cell_size):
                pygame.draw.line(self.screen, GRID_COLOR, 
                               (offset_x + x, offset_y), 
                               (offset_x + x, offset_y + grid_pixel_height), 1)
            for y in range(0, grid_pixel_height + 1, cell_size):
                pygame.draw.line(self.screen, GRID_COLOR, 
                               (offset_x, offset_y + y), 
                               (offset_x + grid_pixel_width, offset_y + y), 1)
            
            # Draw snake
            for i, segment in enumerate(game.snake):
                x = offset_x + segment[0] * cell_size
                y = offset_y + segment[1] * cell_size
                if i == 0:
                    color = tuple(min(255, c + 50) for c in SNAKE_COLOR)
                else:
                    color = SNAKE_COLOR
                pygame.draw.rect(self.screen, color, (x, y, cell_size, cell_size))
            
            # Draw apple
            x = offset_x + game.apple[0] * cell_size
            y = offset_y + game.apple[1] * cell_size
            pygame.draw.rect(self.screen, APPLE_COLOR, (x, y, cell_size, cell_size))
            
            # Draw small info text for this game
            font = pygame.font.Font(None, 18)
            text = font.render(f'#{idx+1} Ep:{episode} S:{score}', True, (255, 255, 255))
            self.screen.blit(text, (offset_x + 5, offset_y + 5))
        
        # Draw info bar at bottom
        info_bar_y = self.games_height
        pygame.draw.rect(self.screen, (20, 20, 20), 
                        (0, info_bar_y, self.window_width, self.info_bar_height))
        
        if games_data:
            # Calculate statistics
            avg_score = sum(g[2] for g in games_data) / len(games_data)
            avg_epsilon = sum(g[3] for g in games_data) / len(games_data)
            
            # Format time helper
            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                if hours > 0:
                    return f"{hours}h {minutes}m {secs}s"
                elif minutes > 0:
                    return f"{minutes}m {secs}s"
                else:
                    return f"{secs}s"
            
            # Create info text
            font = pygame.font.Font(None, 32)
            
            # Calculate percentage
            percentage = (total_episodes / total_target * 100) if total_target > 0 else 0
            
            info_parts = [
                f"Best: {best_score}",
                f"Avg Score: {avg_score:.1f}",
                f"Avg ε: {avg_epsilon:.3f}",
                f"Episodes: {total_episodes:,} / {total_target:,} ({percentage:.3f}%)",
                f"Time: {format_time(elapsed_time)} / {format_time(remaining_time)} / {format_time(elapsed_time + remaining_time)}"
            ]
            info_text = " | ".join(info_parts)
            
            text = font.render(info_text, True, (255, 255, 255))
            # Center text in info bar
            text_rect = text.get_rect(center=(self.window_width // 2, info_bar_y + self.info_bar_height // 2))
            self.screen.blit(text, text_rect)
        
        pygame.display.flip()
        self.clock.tick(GAME_SPEED)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True
    
    def close(self):
        if PYGAME_AVAILABLE:
            pygame.quit()


def train():
    """Train the Snake AI."""
    # Create model directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Initialize
    game = SnakeGame()
    agent = SnakeAgent()
    visualizer = SnakeVisualizer() if SHOW_GAME else None
    
    print(f"Training Snake AI for {EPISODES} episodes")
    print(f"Device: {agent.device}")
    print(f"Visualization: {'Enabled' if SHOW_GAME else 'Disabled'}")
    print(f"Model will be saved to: {MODEL_DIR}")
    print("-" * 60)
    
    # Training statistics
    scores = []
    avg_scores = []
    best_score = 0
    total_steps = 0
    
    for episode in range(1, EPISODES + 1):
        state = game.reset()
        episode_reward = 0
        episode_loss = 0
        loss_count = 0
        
        while True:
            # Select and perform action
            action = agent.select_action(state, training=True)
            next_state, reward, done = game.step(action)
            
            # Store transition
            agent.memory.push(state, action, reward, next_state, done)
            
            # Train
            loss = agent.train_step()
            if loss > 0:
                episode_loss += loss
                loss_count += 1
            
            episode_reward += reward
            state = next_state
            total_steps += 1
            
            # Update target network
            if total_steps % TARGET_UPDATE == 0:
                agent.update_target_network()
            
            # Visualize
            if SHOW_GAME and episode % DISPLAY_INTERVAL == 0:  # Show every Nth episode
                if not visualizer.draw(game, episode, game.score, agent.epsilon):
                    print("Training interrupted by user")
                    agent.save(f"{MODEL_DIR}/{MODEL_NAME}_interrupted")
                    return
            
            if done:
                break
        
        # Decay epsilon
        agent.decay_epsilon()
        
        # Track statistics
        scores.append(game.score)
        avg_score = np.mean(scores[-100:])  # Average of last 100 episodes
        avg_scores.append(avg_score)
        
        # Save best model
        if game.score > best_score:
            best_score = game.score
            agent.save(f"{MODEL_DIR}/{MODEL_NAME}_best")
        
        # Save checkpoint
        if episode % SAVE_INTERVAL == 0:
            agent.save(f"{MODEL_DIR}/{MODEL_NAME}_ep{episode}")
            avg_loss = episode_loss / loss_count if loss_count > 0 else 0
            print(f"Episode {episode}/{EPISODES} | Score: {game.score} | Avg Score: {avg_score:.2f} | "
                  f"Best: {best_score} | ε: {agent.epsilon:.3f} | Loss: {avg_loss:.4f} | Steps: {game.steps}")
    
    # Save final model
    agent.save(f"{MODEL_DIR}/{MODEL_NAME}_final")
    
    if visualizer:
        visualizer.close()
    
    print("-" * 60)
    print(f"Training complete!")
    print(f"Best score: {best_score}")
    print(f"Final average score: {avg_scores[-1]:.2f}")
    print(f"Models saved to: {MODEL_DIR}")


def train_parallel():
    """Train multiple Snake AIs in parallel with shared experience."""
    # Create model directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Initialize multiple games and agents
    num_parallel = PARALLEL_GAMES_H * PARALLEL_GAMES_V
    print(f"Initializing {num_parallel} games ({PARALLEL_GAMES_H} horizontal x {PARALLEL_GAMES_V} vertical)")
    games = [SnakeGame() for _ in range(num_parallel)]
    agents = [SnakeAgent() for _ in range(num_parallel)]
    states = [game.reset() for game in games]
    episode_nums = [1] * num_parallel  # Track episode number for each game
    
    # SHARED EXPERIENCE: Create one replay memory for all agents
    shared_memory = ReplayMemory(MEMORY_SIZE)
    print(f"Created shared replay memory (capacity: {MEMORY_SIZE})")
    
    # Replace each agent's memory with the shared one
    for agent in agents:
        agent.memory = shared_memory
    
    visualizer = SnakeVisualizer() if SHOW_GAME else None
    
    print(f"Training {num_parallel} Snake AIs in parallel for {EPISODES} episodes each")
    print(f"Total target episodes: {num_parallel * EPISODES:,}")
    print(f"All agents share experience via common replay buffer")
    print(f"Device: {agents[0].device}")
    print(f"Visualization: {'Enabled' if SHOW_GAME else 'Disabled'}")
    if visualizer:
        print(f"Visualizer: {visualizer.parallel_games_h}x{visualizer.parallel_games_v} grid, "
              f"window={visualizer.window_width}x{visualizer.window_height}")
    print(f"Model will be saved to: {MODEL_DIR}")
    print("-" * 60)
    
    # Training statistics
    best_score = 0
    max_episode = 0
    step_count = 0
    start_time = time.time()  # Track training start time
    last_time_update = start_time  # Track last time info was updated
    total_target_episodes = num_parallel * EPISODES
    
    # Cached timing values (updated at TIME_UPDATE_INTERVAL)
    cached_elapsed_time = 0
    cached_remaining_time = 0
    cached_total_episodes = 0
    
    # Track which games are done
    game_done = [False] * num_parallel
    
    while max_episode < EPISODES:
        # Run one step for ALL games simultaneously (not sequentially)
        actions = []
        next_states = []
        rewards = []
        dones = []
        
        # Step 1: Select actions for all active games
        for i in range(num_parallel):
            if not game_done[i]:
                action = agents[i].select_action(states[i], training=True)
                actions.append(action)
            else:
                actions.append(None)
        
        # Step 2: Execute all actions simultaneously
        for i in range(num_parallel):
            if not game_done[i]:
                next_state, reward, done = games[i].step(actions[i])
                next_states.append(next_state)
                rewards.append(reward)
                dones.append(done)
                
                # Store transition
                agents[i].memory.push(states[i], actions[i], reward, next_state, done)
                
                # Train
                agents[i].train_step()
                
                states[i] = next_state
                
                if done:
                    # Game finished, record stats
                    if games[i].score > best_score:
                        best_score = games[i].score
                        agents[i].save(f"{MODEL_DIR}/{MODEL_NAME}_best")
                    
                    # Decay epsilon
                    agents[i].decay_epsilon()
                    
                    # Print progress for this game with timing
                    if episode_nums[i] % SAVE_INTERVAL == 0:
                        # Calculate timing
                        elapsed_time = time.time() - start_time
                        progress = max_episode / EPISODES
                        if progress > 0:
                            estimated_total = elapsed_time / progress
                            remaining_time = estimated_total - elapsed_time
                        else:
                            estimated_total = 0
                            remaining_time = 0
                        
                        # Format time as hours:minutes:seconds
                        def format_time(seconds):
                            hours = int(seconds // 3600)
                            minutes = int((seconds % 3600) // 60)
                            secs = int(seconds % 60)
                            if hours > 0:
                                return f"{hours}h {minutes}m {secs}s"
                            elif minutes > 0:
                                return f"{minutes}m {secs}s"
                            else:
                                return f"{secs}s"
                        
                        print(f"  Game {i+1} | Episode {episode_nums[i]}/{EPISODES} | "
                              f"Score: {games[i].score} | ε: {agents[i].epsilon:.3f} | "
                              f"Time: {format_time(elapsed_time)} / {format_time(remaining_time)} / {format_time(estimated_total)}")
                    
                    # Reset game for next episode
                    states[i] = games[i].reset()
                    episode_nums[i] += 1
                    
                    # Check if this game has completed all episodes
                    if episode_nums[i] > EPISODES:
                        game_done[i] = True
                    
                    # Update max episode tracker
                    max_episode = max(episode_nums)
        
        # Visualize all games continuously for parallel mode
        step_count += 1
        if SHOW_GAME:  # Update display every step in parallel mode
            games_data = [(games[i], episode_nums[i], games[i].score, agents[i].epsilon) 
                         for i in range(num_parallel)]
            
            # Calculate timing information (update based on interval)
            current_time = time.time()
            if current_time - last_time_update >= TIME_UPDATE_INTERVAL:
                last_time_update = current_time
                cached_elapsed_time = current_time - start_time
                cached_total_episodes = sum(episode_nums) - num_parallel  # Subtract initial 1s
                progress = cached_total_episodes / total_target_episodes if total_target_episodes > 0 else 0
                if progress > 0:
                    estimated_total = cached_elapsed_time / progress
                    cached_remaining_time = estimated_total - cached_elapsed_time
                else:
                    cached_remaining_time = 0
            
            if step_count == 1:  # Debug on first draw
                print(f"DEBUG: Drawing {len(games_data)} games in parallel")
                print(f"DEBUG: First 3 games - Ep=[{games_data[0][1]}, {games_data[1][1]}, {games_data[2][1]}], "
                      f"Scores=[{games_data[0][2]}, {games_data[1][2]}, {games_data[2][2]}]")
            
            if not visualizer.draw_parallel(games_data, 
                                           total_episodes=cached_total_episodes,
                                           total_target=total_target_episodes,
                                           elapsed_time=cached_elapsed_time,
                                           remaining_time=cached_remaining_time,
                                           best_score=best_score):
                print("Training interrupted by user")
                agents[0].save(f"{MODEL_DIR}/{MODEL_NAME}_interrupted")
                if visualizer:
                    visualizer.close()
                return
        
        # Check if all games are done
        if all(game_done):
            break
    
    # Save final model (from first agent)
    agents[0].save(f"{MODEL_DIR}/{MODEL_NAME}_final")
    
    if visualizer:
        visualizer.close()
    
    # Calculate total training time
    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)
    time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    print("-" * 60)
    print(f"Parallel training complete!")
    print(f"Best score across all games: {best_score}")
    print(f"Total training time: {time_str}")
    print(f"Models saved to: {MODEL_DIR}")
    print("-" * 60)


def play(model_path, episodes=5):
    """Play the game with a trained model."""
    game = SnakeGame()
    agent = SnakeAgent()
    agent.load(model_path)
    agent.epsilon = 0  # No exploration during play
    
    visualizer = SnakeVisualizer() if PYGAME_AVAILABLE else None
    
    print(f"Playing with model: {model_path}")
    print(f"Episodes: {episodes}")
    print("-" * 60)
    
    total_scores = []
    
    for episode in range(1, episodes + 1):
        state = game.reset()
        
        while True:
            action = agent.select_action(state, training=False)
            next_state, reward, done = game.step(action)
            state = next_state
            
            if PYGAME_AVAILABLE:
                if not visualizer.draw(game, episode, game.score, 0):
                    break
            
            if done:
                total_scores.append(game.score)
                print(f"Episode {episode} | Score: {game.score} | Steps: {game.steps}")
                break
    
    if visualizer:
        visualizer.close()
    
    print("-" * 60)
    print(f"Average score: {np.mean(total_scores):.2f}")
    print(f"Best score: {max(total_scores)}")


if __name__ == "__main__":
    import sys
    
    mode = "train"  # Default mode
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    if mode == "train":
        train()
    elif mode == "parallel":
        train_parallel()
    elif mode == "play":
        model_path = f"{MODEL_DIR}/{MODEL_NAME}_best"
        if len(sys.argv) > 2:
            model_path = sys.argv[2]
        play(model_path, episodes=10)
    else:
        print("Usage:")
        print("  Train:           python asnake.py train")
        print("  Train Parallel:  python asnake.py parallel")
        print("  Play:            python asnake.py play [model_path]")
