# -*- mode: python -*-

block_cipher = None

added_files = [
         ( 'gelectrical/interface/*.glade', 'gelectrical/interface' ),
         ( 'gelectrical/interface/*.png', 'gelectrical/interface' ),
         ( 'gelectrical/interface/*.svg', 'gelectrical/interface' ),
         ( 'gelectrical/database/*.csv', 'gelectrical/database' ),
		 ( 'gelectrical/database/*.png', 'gelectrical/database' ),
		 ( 'gelectrical/icons/*.svg', 'gelectrical/icons' ),
		 ( 'gelectrical/templates/*.css', 'gelectrical/templates' ),
		 ( 'gelectrical/templates/*.html', 'gelectrical/templates' ),
		 ( 'gelectrical/templates/*.png', 'gelectrical/templates' ),
		 ( 'gelectrical/templates/*.svg', 'gelectrical/templates' )
		 ]

a = Analysis(['gelectrical_launcher.py'],
             pathex=['C:\\Users\\User\\Desktop\\GElectrical'],
             binaries=None,
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='GElectrical',
          debug=False,
          strip=False,
          upx=False,
          console=False,
          icon = 'GElectrical.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name='ApplicationFiles')
