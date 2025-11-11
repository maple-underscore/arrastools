import numpy as np
import platform
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical, MultivariateNormal
import mss
import time
import threading
import os
from datetime import datetime
from pynput.keyboard import Key, Controller as KeyboardController, Listener as KeyboardListener
from pynput.mouse import Controller as MouseController, Button
from shapely.geometry import Point, Polygon
import random
import sys
import traceback
import pytesseract
from PIL import Image
import re

# Detect platform
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows'
print(f"Arras AI running on: {PLATFORM}")

# Platform notes
if PLATFORM not in ('darwin', 'linux', 'windows'):
    print(f"Warning: Platform '{PLATFORM}' may have limited support.")
    print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")
    print("NOTE: Tesseract OCR must be installed separately on your system.")

# Add global escape flag
keyboard_controller = KeyboardController()
mouse_controller = MouseController()
exit_requested = False
paused = False  # New pause state variable
simulate_death = False  # New flag to simulate death
cooldown_active = False  # Track if we're in cooldown period
last_cooldown_time = 0   # Track when cooldown started
sct = mss.mss()

# Fix escape key handling
def on_press(key):
    global exit_requested, paused, simulate_death
    if key == Key.esc:
        print("Escape pressed - stopping AI")
        exit_requested = True
        os._exit(0)  # Force immediate termination
        return False  # Stop listener
    elif hasattr(key, 'char') and key.char == 'p':
        # Toggle pause state
        paused = not paused
        print(f"AI {'PAUSED' if paused else 'RESUMED'}")
        return True  # Continue listening
    elif hasattr(key, 'char') and key.char == 'r':
        # Simulate death
        print("Manual death triggered via 'r' key")
        simulate_death = True
        return True  # Continue listening

def start_keyboard_listener():
    global keyboard_listener
    keyboard_listener = KeyboardListener(on_press=on_press)
    keyboard_listener.daemon = True  # Make sure thread exits when main program does
    keyboard_listener.start()

# Game region polygon
# NOTE: These coordinates are for a specific screen resolution/layout.
# Adjust GAME_REGION based on your display resolution and scaling.
# Use pixel detection tools to find your game boundaries.
GAME_REGION = Polygon([
    (1701.453125, 356.5390625), 
    (1447.49609375, 361.4921875), 
    (1450.40625, 136.38671875), 
    (36.13671875, 127.40234375), 
    (43.6171875, 1089.2109375), 
    (1476.8515625, 1093.80078125),
    (1686.76953125, 821.2578125)
])

# Possible upgrade paths
upgrade_paths = ['basic', 'twin', 'sniper', 'machine gun', 'pounder', 'flank guard', 'director', 'trapper', 'smasher', 'desmos'
]

def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def is_dead():
    """Check if the player is dead."""
    global simulate_death
    
    # If death was manually triggered
    if simulate_death:
        simulate_death = False  # Reset the flag
        return True
    
    p27930 = get_pixel_rgb(27, 930)
    # Removed print statement for speed - was causing massive slowdown
    if p27930 == (176, 100, 81):
        print(f"Death detected at pixel (27, 930): {p27930}")
        return True
    
    return False

def detect_score():
    """Detect the current score from screen using OCR."""
    try:
        # Capture the screen region containing the score
        bbox = {"top": 529, "left": 692, "width": 1228-692, "height": 592-529}
        screenshot = sct.grab(bbox)
        
        # Save screenshot for debugging
        tmp_file = 'score_capture.png'
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=tmp_file)
        # Removed print for speed
        
        try:
            # Convert to PIL Image for OCR
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            # Use OCR to extract text (configure for digit recognition)
            text = pytesseract.image_to_string(img, config='--psm 7 -c tessedit_char_whitelist=0123456789')
            # Removed verbose OCR print for speed
            
            # Extract numbers using regex
            matches = re.findall(r'\d+', text)
            if matches:
                largest_num = max(int(num) for num in matches)
                print(f"Detected score: {largest_num}")
                return largest_num
                
            return 30000  # Fallback score
        except ImportError:
            print("pytesseract not installed. Install with: pip install pytesseract")
            print("You also need to install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
            return 30000
    except Exception as e:
        print(f"Error detecting score: {e}")
        traceback.print_exc()
        return 30000  # Fallback on error

# Fix the polygon sampling function to actually find points
def sample_points_in_polygon(polygon, step=10):
    """Sample points within polygon at regular intervals."""
    min_x, min_y, max_x, max_y = polygon.bounds
    points = []
    
    for x in range(int(min_x), int(max_x), step):
        for y in range(int(min_y), int(max_y), step):
            p = Point(x, y)
            if polygon.contains(p):
                points.append((x, y))
    
    # Ensure we have at least some points (safety)
    if len(points) < 10:
        # Add polygon vertices as fallback
        for coord in polygon.exterior.coords:
            points.append(coord)
    
    return points[:100]  # Limit to 100 points max for performance

# Sample observation points within game region
# Using step=50 for much faster sampling (was 10, giving 500 points)
OBSERVATION_POINTS = sample_points_in_polygon(GAME_REGION, 50)

class PolicyNetwork(nn.Module):
    def __init__(self, input_dim, action_dim):
        super(PolicyNetwork, self).__init__()
        
        # Shared feature extractor
        self.features = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
        )
        
        # Policy head (discrete actions)
        self.action_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Value head
        self.value_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
        # Mouse position head
        self.mouse_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 4)  # x_mean, x_log_std, y_mean, y_log_std
        )
        
        # Sum42 head - outputs 10 numbers that sum to 42
        self.sum42_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 10),
        )
        
        # Upgrade path head - selects from upgrade_paths
        self.upgrade_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, len(upgrade_paths)),
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        x = self.features(x)
        
        action_probs = self.action_head(x)
        state_value = self.value_head(x)
        
        mouse_params = self.mouse_head(x)
        # Expanded mouse range to cover entire screen (0-1920 x 0-1200)
        mouse_x_mean = 0 + torch.sigmoid(mouse_params[:, 0]) * 1920
        mouse_y_mean = 0 + torch.sigmoid(mouse_params[:, 2]) * 1200
        mouse_x_log_std = mouse_params[:, 1]
        mouse_y_log_std = mouse_params[:, 3]
        
        mouse_mean = torch.cat([mouse_x_mean.unsqueeze(1), mouse_y_mean.unsqueeze(1)], dim=1)
        mouse_log_std = torch.cat([mouse_x_log_std.unsqueeze(1), mouse_y_log_std.unsqueeze(1)], dim=1)
        
        sum42_raw = self.sum42_head(x)
        sum42 = torch.softmax(sum42_raw, dim=1) * 42  # Ensures sum is 42
        
        upgrade_probs = self.upgrade_head(x)
        
        return action_probs, state_value, mouse_mean, mouse_log_std, sum42, upgrade_probs

class PPOMemory:
    def __init__(self, batch_size):
        self.states = []
        self.actions = []
        self.probs = []
        self.vals = []
        self.rewards = []
        self.dones = []
        self.mouse_means = []
        self.mouse_log_stds = []
        self.mouse_actions = []
        self.batch_size = batch_size
        
    def store(self, state, action, prob, val, reward, done, mouse_mean, mouse_log_std, mouse_action):
        self.states.append(state)
        self.actions.append(action)
        self.probs.append(prob)
        self.vals.append(val)
        self.rewards.append(reward)
        self.dones.append(done)
        self.mouse_means.append(mouse_mean)
        self.mouse_log_stds.append(mouse_log_std)
        self.mouse_actions.append(mouse_action)
        
    def clear(self):
        self.states = []
        self.actions = []
        self.probs = []
        self.vals = []
        self.rewards = []
        self.dones = []
        self.mouse_means = []
        self.mouse_log_stds = []
        self.mouse_actions = []
        
    def generate_batches(self):
        n_states = len(self.states)
        
        # Fix 1: Ensure n_states is at least batch_size
        if n_states < self.batch_size:
            # If we don't have enough samples for a batch, just return a single batch with all samples
            return (
                np.array(self.states),
                np.array(self.actions),
                np.array(self.probs),
                np.array(self.vals),
                np.array(self.rewards),
                np.array(self.dones),
                np.array(self.mouse_means),
                np.array(self.mouse_log_stds),
                np.array(self.mouse_actions),
                [np.arange(n_states)]  # Just one batch with all indices
            )
        
        # Calculate batch starts as before
        batch_start = np.arange(0, n_states, self.batch_size)
        indices = np.arange(n_states, dtype=np.int64)
        np.random.shuffle(indices)
        
        # Fix 2: Ensure no batch has indices exceeding array length
        batches = []
        for i in batch_start:
            # Get end index and ensure it doesn't exceed n_states
            end_idx = min(i + self.batch_size, n_states)
            # Only add complete batches (or the final partial batch)
            if end_idx > i:
                batches.append(indices[i:end_idx])
        
        return (
            np.array(self.states),
            np.array(self.actions),
            np.array(self.probs),
            np.array(self.vals),
            np.array(self.rewards),
            np.array(self.dones),
            np.array(self.mouse_means),
            np.array(self.mouse_log_stds),
            np.array(self.mouse_actions),
            batches
        )

class ArrasAI:
    def __init__(self, input_dim, action_dim, learning_rate=0.0003, gamma=0.99, 
                 epsilon=0.2, batch_size=64, n_epochs=10, entropy_coef=0.01):
        self.gamma = gamma
        self.epsilon = epsilon
        self.n_epochs = n_epochs
        self.entropy_coef = entropy_coef
        
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.policy = PolicyNetwork(input_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=learning_rate)
        self.memory = PPOMemory(batch_size)
        
        # Key mapping
        self.action_map = ['w', 'a', 's', 'd', Key.space]
        self.active_keys = set()
        
    def get_action(self, state):
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action_probs, value, mouse_mean, mouse_log_std, sum42, upgrade_probs = self.policy(state)
            
        # Sample discrete action
        action_dist = Categorical(action_probs)
        action = action_dist.sample()
        action_log_prob = action_dist.log_prob(action)
        
        # Improve mouse position variety
        # Increase standard deviation for more exploration
        mouse_std = torch.exp(mouse_log_std) * 1.5  # Increased variance
        cov_matrix = torch.diag_embed(mouse_std.pow(2))
        mouse_dist = MultivariateNormal(mouse_mean, cov_matrix)
        
        # Sample multiple times and take the one furthest from mean
        num_samples = 3
        mouse_samples = []
        for _ in range(num_samples):
            sample = mouse_dist.sample()
            mouse_samples.append(sample)
        
        # Either take random sample or occasionally force uniform random position
        if random.random() < 0.05:  # 5% chance of random position
            mouse_x = random.uniform(0, 1920)
            mouse_y = random.uniform(0, 1200)
            mouse_action = torch.tensor([[mouse_x, mouse_y]], device=self.device)
            mouse_log_prob = mouse_dist.log_prob(mouse_action)
        else:
            mouse_action = mouse_samples[random.randint(0, num_samples-1)]
            mouse_log_prob = mouse_dist.log_prob(mouse_action)
        
        # Clamp mouse position to valid range (expanded to full screen)
        mouse_x = torch.clamp(mouse_action[0, 0], 0, 1920).item()
        mouse_y = torch.clamp(mouse_action[0, 1], 0, 1200).item()
        
        # Get sum42 and upgrade_path
        sum42_values = sum42.squeeze(0).cpu().numpy()
        upgrade_idx = torch.argmax(upgrade_probs.squeeze(0)).item()
        
        return (action.item(), 
                action_log_prob.item(),
                value.item(), 
                mouse_mean.squeeze(0).cpu().numpy(),
                mouse_log_std.squeeze(0).cpu().numpy(),
                (mouse_x, mouse_y),
                mouse_log_prob.item(),
                sum42_values,
                upgrade_idx)
    
    def learn(self):
        for _ in range(self.n_epochs):
            (
                states, 
                actions, 
                old_log_probs, 
                values,
                rewards, 
                dones, 
                old_mouse_means,
                old_mouse_log_stds,
                mouse_actions,
                batches
            ) = self.memory.generate_batches()
            
            advantages = np.zeros(len(rewards), dtype=np.float32)
            
            # Calculate advantages
            for t in range(len(rewards)-1):
                discount = 1
                a_t = 0
                for k in range(t, len(rewards)-1):
                    a_t += discount * (rewards[k] + self.gamma * values[k+1] * (1-dones[k]) - values[k])
                    discount *= self.gamma
                advantages[t] = a_t
                
            advantages = torch.FloatTensor(advantages).to(self.device)
            
            for batch in batches:
                states_batch = torch.FloatTensor(states[batch]).to(self.device)
                actions_batch = torch.LongTensor(actions[batch]).to(self.device)
                old_log_probs_batch = torch.FloatTensor(old_log_probs[batch]).to(self.device)
                mouse_actions_batch = torch.FloatTensor(mouse_actions[batch]).to(self.device)
                
                # Forward pass
                new_action_probs, values_batch, new_mouse_means, new_mouse_log_stds, _, _ = self.policy(states_batch)
                
                # Discrete action loss
                dist = Categorical(new_action_probs)
                new_log_probs = dist.log_prob(actions_batch)
                ratios = torch.exp(new_log_probs - old_log_probs_batch)
                surr1 = ratios * advantages[batch]
                surr2 = torch.clamp(ratios, 1-self.epsilon, 1+self.epsilon) * advantages[batch]
                action_loss = -torch.min(surr1, surr2).mean()
                
                # Mouse position loss
                mouse_stds = torch.exp(new_mouse_log_stds)
                new_mouse_dist = MultivariateNormal(new_mouse_means, torch.diag_embed(mouse_stds.pow(2)))
                
                old_mouse_stds = torch.FloatTensor(np.exp(old_mouse_log_stds[batch])).to(self.device)
                old_mouse_means = torch.FloatTensor(old_mouse_means[batch]).to(self.device)
                
                new_mouse_log_probs = new_mouse_dist.log_prob(mouse_actions_batch)
                old_mouse_dist = MultivariateNormal(old_mouse_means, torch.diag_embed(old_mouse_stds.pow(2)))
                old_mouse_log_probs = old_mouse_dist.log_prob(mouse_actions_batch)
                
                mouse_ratios = torch.exp(new_mouse_log_probs - old_mouse_log_probs)
                mouse_surr1 = mouse_ratios * advantages[batch]
                mouse_surr2 = torch.clamp(mouse_ratios, 1-self.epsilon, 1+self.epsilon) * advantages[batch]
                mouse_loss = -torch.min(mouse_surr1, mouse_surr2).mean()
                
                # Value loss
                returns = advantages[batch] + torch.FloatTensor(values[batch]).to(self.device)
                value_loss = nn.MSELoss()(values_batch.squeeze(), returns)
                
                # Entropy bonus (encourages exploration)
                entropy = dist.entropy().mean() + new_mouse_dist.entropy().mean()
                
                # Total loss
                loss = action_loss + 0.5 * value_loss + mouse_loss - self.entropy_coef * entropy
                
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
                self.optimizer.step()
        
        # Clear memory after learning
        self.memory.clear()
    
    def save_model(self, path):
        torch.save(self.policy.state_dict(), path)
        
    def load_model(self, path):
        self.policy.load_state_dict(torch.load(path))
    
    # Fix the apply_action method to provide debug feedback
    def apply_action(self, action_idx, mouse_pos):
        # Update keys
        target_key = self.action_map[action_idx] if action_idx < len(self.action_map) else None
        
        # Debug print what action we're taking (reduce verbosity)
        if target_key:
            action_name = target_key if target_key != Key.space else "SPACE"
            print(f"Action: {action_name}, Mouse: ({mouse_pos[0]:.0f}, {mouse_pos[1]:.0f})")
        
        # Release all currently held keys except the target key
        for key in list(self.active_keys):
            if key != target_key:
                keyboard_controller.release(key)
                self.active_keys.remove(key)
        
        # Handle Space key - tap it (press and release)
        if target_key == Key.space:
            if target_key not in self.active_keys:
                keyboard_controller.press(Key.space)
                time.sleep(0.05)
                keyboard_controller.release(Key.space)
                print("SPACE tapped")
        # Handle movement keys - hold them down
        elif target_key is not None:
            if target_key not in self.active_keys:
                keyboard_controller.press(target_key)
                self.active_keys.add(target_key)
                print(f"Holding: {target_key}")
            
        # Update mouse position
        mouse_controller.position = mouse_pos

def apply_upgrade_path(path):
    """Apply selected upgrade path to the game."""
    print(f"Selected upgrade path: {path}")
    # In actual implementation: wait for upgrade points and press number keys
    # This is just a placeholder

def get_observation():
    """Get current observation from screen - optimized for speed."""
    try:
        # Print first time to see how many points we're observing
        if not hasattr(get_observation, "first_run"):
            get_observation.first_run = True
            print(f"Sampling {len(OBSERVATION_POINTS)} observation points")
            if len(OBSERVATION_POINTS) == 0:
                print("WARNING: No observation points found in polygon!")

        # OPTIMIZATION: Capture entire screen once instead of per-pixel
        min_x = int(min(x for x, y in OBSERVATION_POINTS))
        max_x = int(max(x for x, y in OBSERVATION_POINTS))
        min_y = int(min(y for x, y in OBSERVATION_POINTS))
        max_y = int(max(y for x, y in OBSERVATION_POINTS))
        
        bbox = {"top": min_y, "left": min_x, "width": max_x - min_x + 1, "height": max_y - min_y + 1}
        screenshot = sct.grab(bbox)
        img_array = np.array(screenshot)[:, :, :3]  # RGB only, drop alpha
        
        obs = []
        for x, y in OBSERVATION_POINTS:
            try:
                # Convert absolute coords to relative coords within screenshot
                rel_x = int(x - min_x)
                rel_y = int(y - min_y)
                rgb = img_array[rel_y, rel_x]
                obs.extend([c/255.0 for c in rgb])  # Normalize colors
            except Exception as e:
                # Use zeros as fallback if point is out of bounds
                obs.extend([0, 0, 0])
                
        return np.array(obs, dtype=np.float32)
    except Exception as e:
        print(f"Error in get_observation(): {e}")
        traceback.print_exc()
        # Return zeros as fallback
        return np.zeros(len(OBSERVATION_POINTS) * 3, dtype=np.float32)

# Fix the train_ai function to properly declare globals
def train_ai(episodes=100, steps_per_episode=2000, save_interval=10, 
             model_dir="models", model_name="arras_model.pt"):
    """Train the AI using PPO."""
    global exit_requested, paused, cooldown_active, last_cooldown_time, simulate_death
    
    try:
        # Start keyboard listener to detect escape key
        start_keyboard_listener()
        
        # Print more diagnostic info
        print(f"Game region bounds: {GAME_REGION.bounds}")
        print(f"Device: {torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')}")
        
        # Prepare model directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize AI
        input_dim = len(OBSERVATION_POINTS) * 3  # RGB values
        print(f"Input dimension: {input_dim}")
        action_dim = 5  # WASD + Space
        
        agent = ArrasAI(input_dim=input_dim, action_dim=action_dim)
        
        best_reward = float('-inf')
        total_steps = 0
        
        print(f"Starting training for {episodes} episodes")
        print(f"Observation points: {len(OBSERVATION_POINTS)}")
        print("Press ESC at any time to stop training")
        
        for episode in range(1, episodes + 1):
            if exit_requested:
                print("Training stopped by user (ESC pressed)")
                break
                
            start_time = time.time()
            state = get_observation()
            episode_reward = 0
            
            # Rate limiting: track last action time for 10 actions per second
            last_action_time = 0
            action_interval = 0.1  # 10 actions per second (100ms between actions)
            
            # Get initial outputs for this episode
            action_idx, action_log_prob, value, mouse_mean, mouse_log_std, mouse_pos, mouse_log_prob, sum42, upgrade_idx = agent.get_action(state)
            
            # Output required values at start
            print(f"Episode {episode} - Initial outputs:")
            print(f"Sum42: {sum42.tolist()} (sum: {sum42.sum():.2f})")
            print(f"Upgrade Path: {upgrade_paths[upgrade_idx]}")
            
            # Apply upgrade path in game (placeholder)
            apply_upgrade_path(upgrade_paths[upgrade_idx])
            
            for step in range(steps_per_episode):
                if exit_requested:
                    break
                    
                # Check if paused - if so, wait until unpaused
                while paused and not exit_requested:
                    time.sleep(0.1)  # Small sleep to prevent CPU spinning
                
                if exit_requested:
                    break
                
                # Handle cooldown period ONLY at the start of episode or after death
                if cooldown_active:
                    current_time = time.time()
                    if (current_time - last_cooldown_time) < 2.0:
                        time.sleep(0.1)  # Small sleep to not burn CPU
                        continue  # Skip taking action
                    else:
                        # Cooldown period is over
                        cooldown_active = False
                        print("Cooldown period ended - resuming actions")
                
                # For the very first step of the episode, start cooldown
                if step == 0:
                    print("Starting episode - waiting 2 seconds before first action")
                    last_cooldown_time = time.time()
                    cooldown_active = True
                    continue  # Skip to next iteration to wait
                
                # Simulate death if flag is set
                if simulate_death or is_dead():
                    done = True
                    score = detect_score()
                    reward = score - 26263
                    print(f"Episode {episode}, Step {step}: Died with score {score}, reward {reward}")
                    
                    # Press enter to restart
                    keyboard_controller.press(Key.enter)
                    time.sleep(0.05)
                    keyboard_controller.release(Key.enter)
                    
                    # Reset simulation death flag
                    simulate_death = False
                else:
                    done = False
                    reward = 0.1  # Small reward for surviving
                
                # Rate limiting: ensure 10 actions per second (0.1s between actions)
                current_time = time.time()
                time_since_last_action = current_time - last_action_time
                if time_since_last_action < action_interval:
                    time.sleep(action_interval - time_since_last_action)
                last_action_time = time.time()
                
                # Take action
                agent.apply_action(action_idx, mouse_pos)
                
                # Get new state
                next_state = get_observation()
                
                # Store experience
                agent.memory.store(state, action_idx, action_log_prob, value, reward, done,
                                 mouse_mean, mouse_log_std, mouse_pos)
                
                # Update state
                state = next_state
                episode_reward += reward
                total_steps += 1
                
                # Get next action
                action_idx, action_log_prob, value, mouse_mean, mouse_log_std, mouse_pos, mouse_log_prob, _, _ = agent.get_action(state)
                
                # End episode if dead
                if done:
                    # If died, set cooldown flag
                    cooldown_active = True
                    last_cooldown_time = time.time()
                    print("Death detected - entering 2-second cooldown")
                    break
                    
                # Update model periodically
                if total_steps % 1024 == 0:
                    agent.learn()
            
            # Learn after episode ends
            if len(agent.memory.states) > 0:
                agent.learn()
            
            # Save model
            if episode_reward > best_reward:
                best_reward = episode_reward
                agent.save_model(f"{model_dir}/{model_name}_best")
                print(f"New best model saved with reward: {best_reward:.2f}")
                
            if episode % save_interval == 0:
                agent.save_model(f"{model_dir}/{model_name}_{episode}")
                
            print(f"Episode {episode}/{episodes} - Reward: {episode_reward:.2f}, Steps: {step+1}, Time: {time.time()-start_time:.2f}s")
        
        # Save final model
        if not exit_requested:
            agent.save_model(f"{model_dir}/{model_name}_final")
            print("Training complete!")
        else:
            # Save interrupted model
            agent.save_model(f"{model_dir}/{model_name}_interrupted")
            print("Training interrupted - partial model saved")
    except Exception as e:
        print(f"Error in train_ai(): {e}")
        traceback.print_exc()

def run_trained_ai(model_path, episodes=5):
    """Run the game using a trained model."""
    global exit_requested
    
    # Start keyboard listener to detect escape key
    start_keyboard_listener()
    
    input_dim = len(OBSERVATION_POINTS) * 3
    action_dim = 5
    
    agent = ArrasAI(input_dim=input_dim, action_dim=action_dim)
    agent.load_model(model_path)
    
    print(f"Running trained model from {model_path} for {episodes} episodes")
    print("Press ESC at any time to stop")
    
    for episode in range(1, episodes + 1):
        if exit_requested:
            print("Execution stopped by user (ESC pressed)")
            break
            
        print(f"Episode {episode} starting...")
        state = get_observation()
        done = False
        steps = 0
        
        # Get initial outputs
        action_idx, _, _, _, _, mouse_pos, _, sum42, upgrade_idx = agent.get_action(state)
        
        print(f"Sum42: {sum42.tolist()} (sum: {sum42.sum():.2f})")
        print(f"Upgrade Path: {upgrade_paths[upgrade_idx]}")
        
        apply_upgrade_path(upgrade_paths[upgrade_idx])
        
        first_run = True
        cooldown_active = False
        last_cooldown_time = 0
        
        # Rate limiting: 10 actions per second
        last_action_time = 0
        action_interval = 0.1  # 10 actions per second (100ms between actions)
        
        while not done and steps < 10000 and not exit_requested:
            # Check if paused - if so, wait until unpaused
            while paused and not exit_requested:
                time.sleep(0.1)  # Small sleep to prevent CPU spinning
            
            if exit_requested:
                break
            
            # Handle cooldown period (first run or after death)
            current_time = time.time()
            if first_run or cooldown_active:
                if first_run:
                    print("Starting episode - waiting 2 seconds before first action")
                    last_cooldown_time = current_time
                    cooldown_active = True
                    first_run = False
                
                # If we're within 2 seconds of last cooldown
                if (current_time - last_cooldown_time) < 2.0:
                    time.sleep(0.1)  # Small sleep to not burn CPU
                    continue  # Skip taking action
                else:
                    # Cooldown period is over
                    cooldown_active = False
                    print("Cooldown period ended - resuming actions")
            
            # Rate limiting: ensure 10 actions per second (0.1s between actions)
            current_time = time.time()
            time_since_last_action = current_time - last_action_time
            if time_since_last_action < action_interval:
                time.sleep(action_interval - time_since_last_action)
            last_action_time = time.time()
            
            # Take action
            agent.apply_action(action_idx, mouse_pos)
            
            # Get new state and action
            state = get_observation()
            action_idx, _, _, _, _, mouse_pos, _, _, _ = agent.get_action(state)
            
            # Check if dead
            if is_dead():
                done = True
                cooldown_active = True
                last_cooldown_time = time.time()
                score = detect_score()
                print(f"Episode {episode}: Died with score {score}")
                print("Death detected - entering 2-second cooldown")
                
                # Press enter to restart
                keyboard_controller.press(Key.enter)
                time.sleep(0.05)
                keyboard_controller.release(Key.enter)
        
            steps += 1
    
    if not exit_requested:
        print("Finished running trained model")
    else:
        print("Execution terminated by user")

if __name__ == "__main__":
    # Configuration
    TRAINING_EPISODES = 200
    STEPS_PER_EPISODE = 2000
    SAVE_INTERVAL = 10
    
    # Create model directory
    MODEL_DIR = "arras_models"
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Train or run model
    train_mode = True
    
    try:
        if train_mode:
            train_ai(
                episodes=TRAINING_EPISODES,
                steps_per_episode=STEPS_PER_EPISODE,
                save_interval=SAVE_INTERVAL,
                model_dir=MODEL_DIR
            )
        else:
            # Replace with your model path
            model_path = f"{MODEL_DIR}/arras_model_best"
            run_trained_ai(model_path, episodes=5)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()