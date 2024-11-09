import sys
import asyncio
from src.core import main
from src.deeplchain import _banner as ge, hju, mrh

if __name__ == "__main__":
    while True:
        ge()
        print(hju + f" Please wait starting your bot...")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print()
            print(mrh + f"Successfully logged out of the bot\n")
            sys.exit()
