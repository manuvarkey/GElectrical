# -*- mode: python -*-

block_cipher = None

added_files = [
         ( 'gelectrical/interface/*.glade', 'gelectrical/interface' ),
         ( 'gelectrical/interface/*.png', 'gelectrical/interface' ),
         ( 'gelectrical/database/*.csv', 'gelectrical/database' ),
         ( 'gelectrical/database/fuse_abb_cef/*.csv', 'gelectrical/database/fuse_abb_cef' ),
         ( 'gelectrical/database/fuse_abb_cef/*.json', 'gelectrical/database/fuse_abb_cef' ),
         ( 'gelectrical/database/fuse_lnt/*.csv', 'gelectrical/database/fuse_lnt' ),
         ( 'gelectrical/database/fuse_lnt/*.json', 'gelectrical/database/fuse_lnt' ),
		 ( 'gelectrical/icons/*.svg', 'gelectrical/icons' ),
		 ( 'gelectrical/templates/*.css', 'gelectrical/templates' ),
		 ( 'gelectrical/templates/*.html', 'gelectrical/templates' )		 ]

a = Analysis(['gelectrical_launcher.py'],
             pathex=['C:\\Users\\User\\Desktop\\GElectrical'],
             binaries=None,
             datas=added_files,
             hiddenimports=['llvmlite'],
             hookspath=[],
             runtime_hooks=[],
			 hooksconfig={"matplotlib": {"backends": ["GTK3Agg" ,"GTK3Cairo", "svg", "pdf"]}},
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
