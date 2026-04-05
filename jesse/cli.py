import time

import click
from importlib.metadata import version as get_version
import uvicorn

import jesse.helpers as jh
from jesse.services.multiprocessing import process_manager
from jesse.services.web import fastapi_app


@click.group()
@click.version_option(get_version("jesse"))
def cli() -> None:
    """Jesse 的 CLI 入口点。"""
    pass


@cli.command()
@click.option(
    "--strict/--no-strict",
    default=True,
    help="默认为严格模式，如果未设置许可证值，将引发异常。",
)
def install_live(strict: bool) -> None:
    """安装并配置实盘交易插件。"""
    from jesse.services.installer import install

    install(is_live_plugin_already_installed=jh.has_live_trade_plugin(), strict=strict)


@cli.command()
def run() -> None:
    """启动 Jesse 应用服务器。"""
    # Display welcome message
    welcome_message = """
     ██╗███████╗███████╗███████╗███████╗
     ██║██╔════╝██╔════╝██╔════╝██╔════╝
     ██║█████╗  ███████╗███████╗█████╗  
██   ██║██╔══╝  ╚════██║╚════██║██╔══╝  
╚█████╔╝███████╗███████║███████║███████╗
 ╚════╝ ╚══════╝╚══════╝╚══════╝╚══════╝
                                        
    """
    version = get_version("jesse")
    print(welcome_message)
    print(f"主框架版本: {version}")

    # Check if jesse-live is installed and display its version
    if jh.has_live_trade_plugin():
        try:
            from jesse_live.version import __version__ as live_version

            print(f"实盘插件版本: {live_version}")
        except ImportError:
            pass

    jh.validate_cwd()

    print("")

    # run all the db migrations
    from jesse.services.migrator import run as run_migrations
    import peewee

    try:
        run_migrations()
    except peewee.OperationalError:
        sleep_seconds = 10
        print(f"数据库未准备好。等待 {sleep_seconds} 秒后重试。")
        time.sleep(sleep_seconds)
        run_migrations()

    # Install Python Language Server if needed
    try:
        from jesse.services.lsp import install_lsp_server

        install_lsp_server()
    except Exception as e:
        print(jh.color(f"安装 Python 语言服务器时出错: {str(e)}", "red"))
        pass

    # read port from .env file, if not found, use default
    from jesse.services.env import ENV_VALUES

    if "APP_PORT" in ENV_VALUES:
        port = int(ENV_VALUES["APP_PORT"])
    else:
        port = 9000

    if "APP_HOST" in ENV_VALUES:
        host = ENV_VALUES["APP_HOST"]
    else:
        host = "0.0.0.0"

    # run the lsp server
    try:
        from jesse.services.lsp import run_lsp_server

        run_lsp_server()
    except Exception as e:
        print(jh.color(f"运行 Python 语言服务器时出错: {str(e)}", "red"))
        pass

    # run the main application
    process_manager.flush()
    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")

