# include default manifest
include("$(PORT_DIR)/boards/manifest.py")

package("drivers", base_path="core")
package("lib", base_path="core")
module("app.py", base_path="core")
module("conf.py", base_path="core")
module("logging.py", base_path="core")
module("main.py", base_path="core")
