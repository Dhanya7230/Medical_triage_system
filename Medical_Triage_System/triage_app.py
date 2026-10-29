import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import mysql.connector
from mysql.connector import Error
import csv

class TriageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medical Triage Management System - Login")
        self.root.geometry("400x300")
        self.db = None
        self.cursor = None
        
        self.setup_login_screen()

    # ================= LOGIN SCREEN =================
    def setup_login_screen(self):
        self.login_frame = tk.Frame(self.root, padx=20, pady=20)
        self.login_frame.pack(expand=True, fill=tk.BOTH)

        tk.Label(self.login_frame, text="Database Connection", font=("Arial", 16, "bold")).pack(pady=10)

        # Host
        tk.Label(self.login_frame, text="Host:").pack(anchor="w")
        self.host_entry = tk.Entry(self.login_frame, width=40)
        self.host_entry.insert(0, "localhost")
        self.host_entry.pack(pady=5)

        # User
        tk.Label(self.login_frame, text="Username:").pack(anchor="w")
        self.user_entry = tk.Entry(self.login_frame, width=40)
        self.user_entry.insert(0, "root")
        self.user_entry.pack(pady=5)

        # Password
        tk.Label(self.login_frame, text="Password:").pack(anchor="w")
        self.password_entry = tk.Entry(self.login_frame, width=40, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(self.login_frame, text="Connect", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), 
                  command=self.connect_to_db).pack(pady=20)

    def connect_to_db(self):
        host = self.host_entry.get()
        user = self.user_entry.get()
        password = self.password_entry.get()

        try:
            self.db = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database="hospital_triage_db"
            )
            self.cursor = self.db.cursor()
            messagebox.showinfo("Success", "Connected to Database successfully!")
            self.login_frame.destroy()
            self.setup_main_dashboard()
        except Error as e:
            messagebox.showerror("Connection Error", f"Failed to connect to database:\n{e}")

    # ================= MAIN DASHBOARD =================
    def setup_main_dashboard(self):
        self.root.title("Medical Triage Management System - Dashboard")
        self.root.geometry("1100x600")

        # Left Control Panel
        control_panel = tk.Frame(self.root, width=200, bg="#2C3E50", padx=10, pady=10)
        control_panel.pack(side=tk.LEFT, fill=tk.Y)

        buttons = [
            ("Add New Patient", self.open_patient_form),
            ("Search Patient", self.search_patient),
            ("Update Vitals/Triage", self.update_patient),
            ("Manage Treatments", self.open_treatment_window), # NEW BUTTON
            ("Discharge/Delete", self.delete_patient),
            ("Show All Patients", self.load_data),
            ("Export CSV", self.export_csv),
            ("Exit", self.root.quit)
        ]

        tk.Label(control_panel, text="Controls", bg="#2C3E50", fg="white", font=("Arial", 14, "bold")).pack(pady=20)

        for text, command in buttons:
            btn = tk.Button(control_panel, text=text, command=command, bg="#34495E", fg="white", 
                            font=("Arial", 10), width=20, pady=5)
            btn.pack(pady=10)

        # Right Display Area
        display_panel = tk.Frame(self.root, padx=10, pady=10)
        display_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        columns = ("ID", "Name", "Age", "Gender", "Symptoms", "Triage", "BP", "HR", "Arrival")
        self.tree = ttk.Treeview(display_panel, columns=columns, show="headings", selectmode="browse")

        # Define headings and columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)
        
        self.tree.column("Symptoms", width=180)
        self.tree.column("Arrival", width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(display_panel, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(expand=True, fill=tk.BOTH)

        self.load_data()

    # ================= DATABASE OPERATIONS =================
    def load_data(self, query="SELECT * FROM patient_records ORDER BY Arrival_Time DESC", params=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            self.cursor.execute(query, params or ())
            rows = self.cursor.fetchall()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Error as e:
            messagebox.showerror("Database Error", f"Error fetching data:\n{e}")

    def open_patient_form(self, patient_id=None):
        form = tk.Toplevel(self.root)
        form.title("Patient Record Form")
        form.geometry("400x450")
        form.grab_set()

        fields = ["Patient_ID", "Name", "Age", "Gender", "Primary_Symptoms", "Triage_Level", "Blood_Pressure", "Heart_Rate"]
        entries = {}

        for idx, field in enumerate(fields):
            tk.Label(form, text=field.replace("_", " ") + ":").grid(row=idx, column=0, padx=20, pady=10, sticky="w")
            
            if field == "Triage_Level":
                entry = ttk.Combobox(form, values=["Red/Immediate", "Yellow/Urgent", "Green/Delayed"], state="readonly")
            elif field == "Gender":
                entry = ttk.Combobox(form, values=["Male", "Female", "Other"], state="readonly")
            else:
                entry = tk.Entry(form, width=30)
                
            entry.grid(row=idx, column=1, padx=20, pady=10)
            entries[field] = entry

        # If updating, pre-fill data
        if patient_id:
            try:
                self.cursor.execute("SELECT * FROM patient_records WHERE Patient_ID = %s", (patient_id,))
                record = self.cursor.fetchone()
                if record:
                    for i, field in enumerate(fields):
                        entries[field].insert(0, record[i] if record[i] is not None else "")
                    entries["Patient_ID"].config(state="disabled") # Prevent ID change
            except Error as e:
                messagebox.showerror("Error", str(e))
                return

        def save_data():
            data = {f: entries[f].get() for f in fields}
            
            # Validation
            if not data["Patient_ID"] or not data["Name"] or not data["Triage_Level"]:
                messagebox.showwarning("Validation Error", "Patient ID, Name, and Triage Level are required.")
                return

            try:
                if patient_id: # Update
                    query = """UPDATE patient_records SET Name=%s, Age=%s, Gender=%s, 
                               Primary_Symptoms=%s, Triage_Level=%s, Blood_Pressure=%s, Heart_Rate=%s 
                               WHERE Patient_ID=%s"""
                    vals = (data["Name"], data["Age"], data["Gender"], data["Primary_Symptoms"], 
                            data["Triage_Level"], data["Blood_Pressure"], data["Heart_Rate"], patient_id)
                else: # Insert
                    query = """INSERT INTO patient_records (Patient_ID, Name, Age, Gender, Primary_Symptoms, 
                               Triage_Level, Blood_Pressure, Heart_Rate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    vals = (data["Patient_ID"], data["Name"], data["Age"], data["Gender"], data["Primary_Symptoms"], 
                            data["Triage_Level"], data["Blood_Pressure"], data["Heart_Rate"])
                
                self.cursor.execute(query, vals)
                self.db.commit()
                messagebox.showinfo("Success", "Record saved successfully!")
                form.destroy()
                self.load_data()
            except Error as e:
                messagebox.showerror("Database Error", str(e))

        tk.Button(form, text="Save Record", bg="#4CAF50", fg="white", command=save_data).grid(row=len(fields), columnspan=2, pady=20)

    def search_patient(self):
        term = simpledialog.askstring("Search", "Enter Patient ID or Name:")
        if term:
            query = "SELECT * FROM patient_records WHERE Patient_ID LIKE %s OR Name LIKE %s"
            self.load_data(query, (f"%{term}%", f"%{term}%"))

    def update_patient(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a patient from the list first.")
            return
        
        patient_id = self.tree.item(selected[0])['values'][0]
        self.open_patient_form(patient_id=patient_id)

    # ================= TREATMENTS & MEDICATIONS =================
    def open_treatment_window(self):
        # 1. Ensure a patient is selected first
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a patient from the main dashboard first.")
            return
        
        patient_id = self.tree.item(selected[0])['values'][0]
        patient_name = self.tree.item(selected[0])['values'][1]

        # 2. Setup the Sub-Window
        treat_win = tk.Toplevel(self.root)
        treat_win.title(f"Treatments & Medications - {patient_name} ({patient_id})")
        treat_win.geometry("600x500")
        treat_win.grab_set()

        # 3. Add Medication Form (Top Half)
        form_frame = tk.Frame(treat_win, pady=10)
        form_frame.pack(fill=tk.X)

        tk.Label(form_frame, text="Medication Name:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        med_entry = tk.Entry(form_frame, width=30)
        med_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Dosage (e.g., 50mg):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        dose_entry = tk.Entry(form_frame, width=30)
        dose_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Instructions:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        inst_entry = tk.Entry(form_frame, width=30)
        inst_entry.grid(row=2, column=1, padx=10, pady=5)

        # 4. Medication History Table (Bottom Half)
        tree_frame = tk.Frame(treat_win, pady=10)
        tree_frame.pack(expand=True, fill=tk.BOTH)

        cols = ("ID", "Medication", "Dosage", "Instructions", "Date Prescribed")
        treat_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        for col in cols:
            treat_tree.heading(col, text=col)
            treat_tree.column(col, width=110, anchor=tk.CENTER)
        treat_tree.pack(expand=True, fill=tk.BOTH, padx=10)

        # Helper function to load data into this specific tree
        def load_treatments():
            for item in treat_tree.get_children():
                treat_tree.delete(item)
            try:
                self.cursor.execute("SELECT Treatment_ID, Medication_Name, Dosage, Instructions, Prescribed_Date FROM treatments WHERE Patient_ID = %s ORDER BY Prescribed_Date DESC", (patient_id,))
                for row in self.cursor.fetchall():
                    treat_tree.insert("", tk.END, values=row)
            except Error as e:
                messagebox.showerror("Database Error", str(e))

        # Helper function to save a new medication
        def save_treatment():
            med = med_entry.get()
            dose = dose_entry.get()
            inst = inst_entry.get()

            if not med or not dose:
                messagebox.showwarning("Validation", "Medication Name and Dosage are required.")
                return

            try:
                self.cursor.execute("""
                    INSERT INTO treatments (Patient_ID, Medication_Name, Dosage, Instructions) 
                    VALUES (%s, %s, %s, %s)
                """, (patient_id, med, dose, inst))
                self.db.commit()
                med_entry.delete(0, tk.END)
                dose_entry.delete(0, tk.END)
                inst_entry.delete(0, tk.END)
                load_treatments() # Refresh the table
            except Error as e:
                messagebox.showerror("Database Error", str(e))

        tk.Button(form_frame, text="Add Medication", bg="#3498DB", fg="white", command=save_treatment).grid(row=3, column=1, pady=10, sticky="w")

        # Load existing treatments when the window opens
        load_treatments()

    def delete_patient(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a patient to discharge.")
            return
        
        patient_id = self.tree.item(selected[0])['values'][0]
        confirm = messagebox.askyesno("Confirm Discharge", f"Are you sure you want to discharge/delete Patient {patient_id}?")
        
        if confirm:
            try:
                self.cursor.execute("DELETE FROM patient_records WHERE Patient_ID = %s", (patient_id,))
                self.db.commit()
                messagebox.showinfo("Success", "Patient discharged successfully.")
                self.load_data()
            except Error as e:
                messagebox.showerror("Error", str(e))

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        
        try:
            self.cursor.execute("SELECT * FROM patient_records ORDER BY Arrival_Time DESC")
            rows = self.cursor.fetchall()
            headers = [i[0] for i in self.cursor.description]
            
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
                
            messagebox.showinfo("Success", f"Data exported successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = TriageApp(root)
    root.mainloop()