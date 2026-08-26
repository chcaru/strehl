$py  = 'experiments\ORCH-drift-check\cafringe.py'
$out = 'C:\dev\strehl-out\V-ca\census'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$pairs = @(
 @('bee-1-cpl',       'C:\dev\strehl-out\GALLERY-FIXED-SRGB\bee-1-cpl.tiff',       'C:\dev\strehl-out\REVIEW\ca\bee-1-cpl--cafix.tiff'),
 @('coffee-bubbles',  'C:\dev\strehl-out\GALLERY-FIXED-SRGB\coffee-bubbles.tiff',  'C:\dev\strehl-out\V-ca\coffee-bubbles--cafix.tiff'),
 @('foam',            'C:\dev\strehl-out\GALLERY-FIXED-SRGB\foam.tiff',            'C:\dev\strehl-out\V-ca\foam--cafix.tiff'),
 @('couch-fibers-cpl','C:\dev\strehl-out\GALLERY-FIXED-SRGB\couch-fibers-cpl.tiff','C:\dev\strehl-out\V-ca\couch-fibers-cpl--cafix.tiff'),
 @('flowers-cpl',     'C:\dev\strehl-out\GALLERY-FIXED-SRGB\flowers-cpl.tiff',     'C:\dev\strehl-out\V-ca\flowers-cpl--cafix.tiff'),
 @('wrapped-text-1',  'C:\dev\strehl-out\GALLERY-FIXED-SRGB\wrapped-text-1.tiff',  'C:\dev\strehl-out\V-ca\wrapped-text-1--cafix.tiff')
)
foreach($p in $pairs){
  "########## $($p[0]) ##########"
  python $py $p[1] $p[2] $out 2>&1
}
