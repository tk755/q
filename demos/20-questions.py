import argparse
import os
import random
import sys
import time

# Add parent directory to path to import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import ChatAgent, OpenAIClient


# Model configuration
MODEL = "gpt-5.1"


# ANSI color codes
class Color:
    QUESTION = '\033[93m' # yellow
    ANSWER = '\033[94m' # blue
    INFO = '\033[90m' # gray
    BOLD = '\033[1m'
    RESET = '\033[0m'


def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def type_text(text: str, delay: float = 0.02):
    """Print text with typing animation."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def is_word_valid(client: OpenAIClient, word: str) -> bool:
    """Check if the generated word is suitable for 20 questions."""
    validator = ChatAgent(
        client=client,
        model=MODEL,
        system_prompt="You are a validator for 20 questions game words. A good word is: a concrete noun or proper noun, well-known, unambiguous, and fun to guess. Bad words are: too uncommon, too abstract, or longer than one word. Respond with ONLY 'VALID' or 'INVALID'."
    )
    result = validator.prompt(f"Is '{word}' a good word for 20 questions?")
    return "VALID" in result.upper()


def generate_word(client: OpenAIClient, max_attempts: int = 3) -> str:
    """Generate a random word for the game using random character hints."""
    word_agent = ChatAgent(
        client=client,
        model=MODEL,
        system_prompt="You are to think of a creative word that is either a noun or proper noun for an exciting game of 20 questions. Respond with only the word itself, and nothing else."
    )

    for _ in range(max_attempts):
        rand_chars = ','.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(1, 2)))
        word = word_agent.prompt(f"Think of a real word that contains the characters {rand_chars}").strip()

        # Validate the word
        if is_word_valid(client, word):
            return word

    # If all attempts fail, return the last word
    return word


def create_questioner(client: OpenAIClient) -> ChatAgent:
    """Create the agent that asks questions to guess the word."""
    return ChatAgent(
        client=client,
        model=MODEL,
        system_prompt="You are playing 20 questions. You must ask 20 yes/no questions one at a time to eventually guess the word. After each question, wait for the user's answer before proceeding. On the 20th question, you must guess the word. Ask intelligent questions by branching broadly as opposed to asking narrow questions which don't reveal as much information. The word is either a noun or proper noun. Respond with ONLY your question, no labels, prefixes, or formatting."
    )


def create_answerer(client: OpenAIClient, word: str) -> ChatAgent:
    """Create the agent that knows the word and answers questions."""
    return ChatAgent(
        client=client,
        model=MODEL,
        system_prompt=f"You are playing 20 questions, and your word is '{word}'. You must accurately answer each question with a single 'Yes' or 'No', followed by a very short and unrevealing quip about the question. This quip must not give any hints about the word. However after question 10 if the user is very clearly off track, you may provide very subtle steering with this quip. After the user's final guess on the 20th question, you may reveal your word. Respond with ONLY your answer, no labels, prefixes, or formatting."
    )


def create_judge(client: OpenAIClient, word: str | None = None) -> ChatAgent:
    """Create the agent that detects if the word was correctly guessed."""
    system_prompt = "You are a judge for a game of 20 questions. "
    if word is not None:
        system_prompt += "The secret word is '{word}'. "
    system_prompt += "You will receive the latest question and answer. Determine if the guesser correctly identified the word AND the answerer confirmed it. Respond with ONLY 'YES' if the word was guessed correctly, or 'NO' if not."

    return ChatAgent(
        client=client,
        model=MODEL,
        system_prompt=system_prompt
    )


def word_was_guessed(judge: ChatAgent, question: str, answer: str) -> bool:
    """Check if the word was correctly guessed in this exchange.

    Returns:
        True if the word was guessed correctly, False otherwise
    """
    exchange = f"Question: {question}\nAnswer: {answer}"
    result = judge.prompt(exchange).strip().upper()
    return "YES" in result


def play_game(client: OpenAIClient, play_as_questioner: bool = False, play_as_answerer: bool = False, word: str | None = None, max_rounds: int = 20):
    """Play a game of 20 questions between two AI agents or with a human player."""
    clear_screen()

    # Welcome banner
    print(f"{Color.BOLD}{Color.INFO}20 Questions with {MODEL}{Color.RESET}\n")

    # Generate word only if not playing as answerer
    if not play_as_answerer and word is None:
        print(f"{Color.INFO}Generating word...{Color.RESET}", end='\r')
        word = generate_word(client)
        print(" " * 20, end='\r')  # Clear "Generating word..." message

    # Show word in spectator mode
    if word is not None and not play_as_questioner:
        type_text(f"{Color.INFO}The word is: {Color.BOLD}{word}{Color.RESET}\n")

    # Create agents
    questioner = None if play_as_questioner else create_questioner(client)
    answerer = None if play_as_answerer else create_answerer(client, word)
    judge = create_judge(client, word if not play_as_answerer else None)

    # Play game
    text = "Begin the game by asking your first question."
    for round_num in range(1, max_rounds + 1):
        # Questioner asks (human or AI)
        if play_as_questioner:
            question = input(f"{Color.QUESTION}Q{round_num}: {Color.RESET}").strip()
        else:
            print(f"{Color.INFO}AI is thinking...{Color.RESET}", end='\r')
            question = questioner.prompt(text)
            print(" " * 20, end='\r')  # Clear "thinking" message
            type_text(f"{Color.QUESTION}Q{round_num}: {question}{Color.RESET}")

        question_formatted = f"Q{round_num}: {question}"

        # Answerer responds (human or AI)
        if play_as_answerer:
            answer = input(f"{Color.ANSWER}A{round_num}: {Color.RESET}").strip()
        else:
            print(f"{Color.INFO}AI is thinking...{Color.RESET}", end='\r')
            answer = answerer.prompt(question_formatted)
            print(" " * 20, end='\r')  # Clear "thinking" message
            type_text(f"{Color.ANSWER}A{round_num}: {answer}{Color.RESET}")
        print()  # Extra line for spacing

        answer_formatted = f"A{round_num}: {answer}"

        # Check if word was guessed
        print(f"{Color.INFO}AI is judging...{Color.RESET}", end='\r')
        guessed = word_was_guessed(judge, question, answer)
        print(" " * 20, end='\r')  # Clear judging message

        if guessed:
            print(f"{Color.BOLD}{Color.INFO}Game over! The word was guessed in {round_num} rounds.{Color.RESET}")
            break

        text = answer_formatted

    # If loop completes without break, max rounds reached
    else:
        if word is not None:
            print(f"{Color.BOLD}{Color.INFO}Game over! The word was: {word}{Color.RESET}")
        else:
            print(f"{Color.BOLD}{Color.INFO}Game over!{Color.RESET}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play 20 questions with AI agents")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-q", "--questioner", action="store_true",
                           help="Play as the questioner (guess the word)")
    mode_group.add_argument("-a", "--answerer", action="store_true",
                           help="Play as the answerer (answer questions about your word)")
    mode_group.add_argument("-w", "--word", type=str,
                           help="Watch AI guess your word")
    parser.add_argument("-m", "--model", type=str,
                       help=f"Override the default model (default: {MODEL})")
    args = parser.parse_args()

    # Override MODEL if specified
    if args.model:
        MODEL = args.model

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    try:
        client = OpenAIClient(api_key=api_key)
        play_game(client, play_as_questioner=args.questioner, play_as_answerer=args.answerer, word=args.word)
    except KeyboardInterrupt:
        print(f"\n\n{Color.INFO}Game terminated.{Color.RESET}")
        sys.exit(0)
