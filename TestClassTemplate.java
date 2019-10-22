package <packageName>;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

public class Test<ClassName> extends TestSQLInjection {
	public Test<ClassName>() {
		super();
	}

	private static final Map<String, String> testInfo = new HashMap<String, String>() {
		{
			put("Asset", "<targetAsset>");
			put("Line No.", "<targetLineNo>");
			put("Findings", "<targetFindings>");
			put("TestClass", Test<ClassName>.class.getCanonicalName());
		}
	};
	
	public static void main(String[] args) throws Throwable {
		Test<ClassName> klaz = new Test<ClassName>();
	}

	@Override
	protected void beforeQuery(Object... args) throws SQLException {

	}

	@Override
	protected void afterQuery(Object... args) throws SQLException {

	}
}
