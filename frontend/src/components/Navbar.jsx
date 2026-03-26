import "../App.css";

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="logo">AI-NutriCare 🥗</div>

      <div className="nav-buttons">
        <button className="btn-outline">Login</button>
        <button className="btn-filled">Sign Up</button>
      </div>
    </nav>
  );
}