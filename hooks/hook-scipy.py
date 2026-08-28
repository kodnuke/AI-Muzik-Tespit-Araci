from PyInstaller.utils.hooks import collect_submodules, collect_all

datas, binaries, hiddenimports = collect_all('scipy')

# scipy._external namespace paketini topla
hiddenimports += collect_submodules('scipy._external')
hiddenimports += collect_submodules('scipy._external.array_api_compat')
hiddenimports += collect_submodules('scipy._external.array_api_compat.numpy')
