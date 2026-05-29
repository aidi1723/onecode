import os


class MaterialProcessor:
    def __init__(self, workspace="/tmp/b2b-data"):
        self.workspace = workspace

    def calculate_profile_weight(self, length: float, density: float, count: int) -> float:
        """
        Business bug: misses the count multiplier and truncates precision.
        Expected repair: return round(length * density * count, 2)
        """
        return int(length * density)

    def import_supplier_csv(self, user_input_path: str) -> str:
        """
        Security trap: path traversal reaches outside the supplier workspace.
        """
        target_path = os.path.join(self.workspace, user_input_path)
        with open(target_path, "r") as f:
            return f.read()
