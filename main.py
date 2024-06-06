import dtlpy as dl
import uvicorn


port = 3000


class Runner(dl.BaseServiceRunner):
    def __init__(self):
        uvicorn.run("app:app",
                    host="0.0.0.0",
                    port=port,
                    timeout_keep_alive=60
                    )


if __name__ == "__main__":
    run = Runner()
