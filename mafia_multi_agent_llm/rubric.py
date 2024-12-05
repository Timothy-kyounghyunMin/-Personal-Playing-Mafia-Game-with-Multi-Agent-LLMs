import matplotlib.pyplot as plt
import numpy as np

# Data from the image
rubrics = [
    "Understanding of Rules", "Coherence", "Correctness", 
    "Interaction Level", "Deductive Reasoning", 
    "Deception and Bluffing", "Responsiveness to Suspicion"
]
chatgpt_baseline = [3.7, 2.775, 3.275, 3.55, 2.65, 3.425, 2.75]
chatgpt_final = [3.675, 2.9, 3.25, 3.65, 2.8, 3.475, 2.975]
human_baseline = [3, 3.67, 2.67, 2.67, 3, 4.33, 4.33]
human_final = [3.67, 2, 4, 3.67, 3.33, 3.67, 4.33]

x = np.arange(len(rubrics))  # X-axis positions
width = 0.35  # Width of the bars

# Plot for ChatGPT evaluations
fig1, ax1 = plt.subplots(figsize=(10, 6))
ax1.bar(x - width/2, chatgpt_baseline, width, label='ChatGPT (Baseline)')
ax1.bar(x + width/2, chatgpt_final, width, label='ChatGPT (Final)')

# Adding labels and title
ax1.set_xlabel('Rubrics', fontsize=12)
ax1.set_ylabel('Scores', fontsize=12)
ax1.set_title('ChatGPT Evaluation Comparison', fontsize=14)
ax1.set_xticks(x)
ax1.set_xticklabels(rubrics, rotation=45, ha="right", fontsize=10)
ax1.legend(fontsize=10)
ax1.set_ylim(0, 5)

# Display grid for better readability
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Save the ChatGPT evaluation plot
plt.tight_layout()
plt.savefig('Mafia_Game_Chatgpt_Comparison.png', dpi=300)

# Plot for Human evaluations
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.bar(x - width/2, human_baseline, width, label='Human (Baseline)')
ax2.bar(x + width/2, human_final, width, label='Human (Final)')

# Adding labels and title
ax2.set_xlabel('Rubrics', fontsize=12)
ax2.set_ylabel('Scores', fontsize=12)
ax2.set_title('Human Evaluation Comparison', fontsize=14)
ax2.set_xticks(x)
ax2.set_xticklabels(rubrics, rotation=45, ha="right", fontsize=10)
ax2.legend(fontsize=10)
ax2.set_ylim(0, 5)

# Display grid for better readability
ax2.grid(axis='y', linestyle='--', alpha=0.7)

# Save the Human evaluation plot
plt.tight_layout()

plt.savefig('Mafia_Game_Human_Comparison.png', dpi=300)
# Show the plots
plt.show()
