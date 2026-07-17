import asyncio

from ai_hunger_games.main import main as run_main
from ai_hunger_games.main import parse_arguments

if __name__ == "__main__":
    arguments = parse_arguments()
    asyncio.run(
        run_main(
            arguments.generations,
            new_experiment_name=arguments.new_experiment,
            experiment_id=arguments.experiment_id,
            list_experiments=arguments.list_experiments,
        )
    )
