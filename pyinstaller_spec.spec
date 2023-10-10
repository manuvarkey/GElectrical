# -*- mode: python -*-

block_cipher = None

added_files = [
         ( 'gelectrical/interface/*.glade', 'gelectrical/interface' ),
		 ( 'gelectrical/interface/*.ui', 'gelectrical/interface' ),
         ( 'gelectrical/interface/*.png', 'gelectrical/interface' ),
         ( 'gelectrical/database/*.csv', 'gelectrical/database' ),
         ( 'gelectrical/database/acb_legrand/*.json', 'gelectrical/database/acb_legrand' ),
         ( 'gelectrical/database/acb_lnt/*.json', 'gelectrical/database/acb_lnt' ),
         ( 'gelectrical/database/acb_schneider/*.json', 'gelectrical/database/acb_schneider' ),
         ( 'gelectrical/database/fuse_abb_cef/*.csv', 'gelectrical/database/fuse_abb_cef' ),
         ( 'gelectrical/database/fuse_abb_cef/*.json', 'gelectrical/database/fuse_abb_cef' ),
         ( 'gelectrical/database/fuse_lnt/*.csv', 'gelectrical/database/fuse_lnt' ),
         ( 'gelectrical/database/fuse_lnt/*.json', 'gelectrical/database/fuse_lnt' ),
		 ( 'gelectrical/database/fuse_schneider/*.csv', 'gelectrical/database/fuse_schneider' ),
         ( 'gelectrical/database/fuse_schneider/*.json', 'gelectrical/database/fuse_schneider' ),
         ( 'gelectrical/database/mcb_legrand/*.json', 'gelectrical/database/mcb_legrand' ),
         ( 'gelectrical/database/mcb_lnt/*.json', 'gelectrical/database/mcb_lnt' ),
         ( 'gelectrical/database/mcb_schneider/*.json', 'gelectrical/database/mcb_schneider' ),
         ( 'gelectrical/database/mccb_legrand/*.json', 'gelectrical/database/mccb_legrand' ),
         ( 'gelectrical/database/mccb_lnt/*.json', 'gelectrical/database/mccb_lnt' ),
         ( 'gelectrical/database/mccb_schneider/*.json', 'gelectrical/database/mccb_schneider' ),
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
