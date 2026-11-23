import argparse
import secrets

from .store import audit, database, initialize, issue


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    add = sub.add_parser("issue")
    add.add_argument("identity")
    add.add_argument("role", choices=["founder", "reader", "emitter", "indexer"])
    add.add_argument("scope", help="Project ID, or * for Founder")
    sub.add_parser("revoke").add_argument("identity")
    args = parser.parse_args()
    if args.command == "init":
        initialize()
    elif args.command == "issue":
        if args.scope == "*" and args.role != "founder":
            parser.error("Only Founder may use global scope")
        print(issue(args.identity, args.role, args.scope))
    else:
        with database() as db:
            row = db.execute("UPDATE identities SET digest=? WHERE id=? RETURNING scope",
                             (secrets.token_hex(48), args.identity)).fetchone()
            if not row:
                parser.error("Unknown identity")
            audit(db, row[0], "local-admin", "revoke", args.identity)


if __name__ == "__main__":
    main()
